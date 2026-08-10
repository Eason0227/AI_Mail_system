"""公司環境資料來源。

讀取 personal_assistant_v2 pipeline 的輸出目錄::

    <REAL_DATA_DIR>/
        <批次資料夾>/                       例如 2026-08-07、2026-08-07-MAIL41_TO_MAIL64
            mails/mail_NNNN/mail.json
            mails/mail_NNNN/body_image_*.gif
            summaries/mail_NNNN_summary.json
            daily_digest.md

同一天可能被切成多個批次資料夾，因此一律掃描所有子資料夾後依 mail_id 合併。

介面與 MockMailRepository 完全相同，Service 以上不需要知道用的是哪一個實作。
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .. import config
from ..models import (
    AIAnalysis,
    BriefHighlight,
    DailyBrief,
    Mail,
    MailCategory,
    SystemAlert,
)
from ..utils import fmt_datetime_label, parse_iso, parse_iso_date
from .adapters.company_adapter import CompanyMailAdapter
from .base_mail_repository import BaseMailRepository

#: 今日重點最多列幾條。
_BRIEF_LIMIT = 5


class RealMailRepository(BaseMailRepository):
    """以公司 pipeline 輸出為資料來源的 Repository。"""

    source_name = "Lotus Notes (公司 pipeline)"

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        today: Optional[date] = None,
    ) -> None:
        self._data_dir = Path(data_dir or config.REAL_DATA_DIR)
        self._today = today or date.today()

        #: mail_id → 該封信資料夾相對於 REAL_DATA_DIR 的路徑（組圖片 URL 用）
        self._mail_dirs: Dict[str, str] = {}

        #: 日期 → 該日期的批次資料夾（同一天可能被切成多個資料夾）
        self._batches_by_date: Dict[date, List[Path]] = {}
        self._selected_date: Optional[date] = None

        self._adapter = self._build_adapter(self._today)

        self._mails: List[Mail] = []
        self._mail_index: Dict[str, Mail] = {}
        self._alerts: List[SystemAlert] = []
        self._brief: DailyBrief = DailyBrief()
        self._loaded_at: datetime = datetime.now()
        self._load_error: str = ""
        self._batch_count: int = 0

        self.refresh()

    def _build_adapter(self, today: date) -> CompanyMailAdapter:
        """建立 Adapter。切換日期時要重建，「今天/昨天」的判斷才會跟著變。"""
        return CompanyMailAdapter(
            today=today,
            asset_url_builder=self._build_asset_url,
            key_person_keywords=config.KEY_PERSON_KEYWORDS,
        )

    # ==================================================================
    # 日期切換
    # ==================================================================
    def _scan_batches(self) -> Dict[date, List[Path]]:
        """掃描輸出目錄，依資料夾名稱開頭的日期分組。

        資料夾命名慣例是 ``YYYY-MM-DD`` 或 ``YYYY-MM-DD-<批次後綴>``，
        例如 ``2026-08-07`` 與 ``2026-08-07-MAIL41_TO_MAIL64`` 屬於同一天。
        """
        grouped: Dict[date, List[Path]] = {}
        if not self._data_dir.is_dir():
            return grouped

        for path in sorted(p for p in self._data_dir.iterdir() if p.is_dir()):
            parsed = parse_iso_date(path.name[:10])
            if parsed is None:
                continue
            grouped.setdefault(parsed, []).append(path)
        return grouped

    @property
    def available_dates(self) -> List[date]:
        return sorted(self._batches_by_date.keys(), reverse=True)

    @property
    def selected_date(self) -> Optional[date]:
        return self._selected_date

    def select_date(self, value: date) -> None:
        """切換檢視日期並重新載入該日資料。"""
        if value not in self._batches_by_date:
            return
        self._selected_date = value
        self._load_selected()

    def _resolve_default_date(self) -> Optional[date]:
        """預設檢視日期：優先今天，今天沒有資料時退回最近的一天。"""
        if not self._batches_by_date:
            return None
        if self._today in self._batches_by_date:
            return self._today
        return max(self._batches_by_date.keys())

    # ==================================================================
    # 載入
    # ==================================================================
    def refresh(self) -> None:
        """重新掃描輸出目錄，並重新載入目前選定的日期。"""
        self._batches_by_date = self._scan_batches()

        # 目前選的日期在重新掃描後可能已經不存在（資料夾被移走）。
        if self._selected_date not in self._batches_by_date:
            self._selected_date = self._resolve_default_date()

        self._load_selected()

    def _load_selected(self) -> None:
        """載入 self._selected_date 那一天的所有批次。"""
        self._load_error = ""
        self._mails, self._mail_index, self._alerts = [], {}, []
        self._mail_dirs = {}
        self._brief = DailyBrief()
        self._loaded_at = datetime.now()

        if not self._data_dir.is_dir():
            self._load_error = f"找不到公司資料目錄：{self._data_dir}"
            return

        if self._selected_date is None:
            self._load_error = (
                f"目錄下沒有任何以日期命名的批次資料夾：{self._data_dir}"
            )
            return

        # 切換日期後「今天/昨天」的基準要跟著換，因此重建 Adapter。
        self._adapter = self._build_adapter(self._selected_date)

        raw_mails: Dict[str, Dict[str, Any]] = {}
        raw_summaries: Dict[str, Dict[str, Any]] = {}
        digest_texts: List[str] = []

        batches = self._batches_by_date[self._selected_date]
        self._batch_count = len(batches)

        for batch in batches:
            for mail_path in sorted(batch.glob("mails/*/mail.json")):
                data = self._read_json(mail_path)
                mail_id = str(data.get("mail_id") or mail_path.parent.name)
                if not mail_id:
                    continue
                raw_mails[mail_id] = data
                # 圖片 URL 需要「這封信的資料夾在哪」，先記下來。
                self._mail_dirs[mail_id] = (
                    mail_path.parent.relative_to(self._data_dir).as_posix()
                )

            for summary_path in sorted(batch.glob("summaries/*_summary.json")):
                data = self._read_json(summary_path)
                mail_id = str(
                    data.get("mail_id")
                    or summary_path.stem.replace("_summary", "")
                )
                if mail_id:
                    raw_summaries[mail_id] = data

            digest = batch / "daily_digest.md"
            if digest.is_file():
                try:
                    digest_texts.append(digest.read_text(encoding="utf-8"))
                except OSError:
                    pass

        if not raw_mails:
            self._load_error = (
                f"{self._selected_date} 這一天沒有任何 mail.json"
            )
            return

        # ---- 郵件 ----
        self._mails = [
            self._adapter.to_mail(raw, raw_summaries.get(mail_id))
            for mail_id, raw in raw_mails.items()
        ]
        # 公司資料只有日期沒有時間，同一天的信改用 mail_id 排序。
        # mail_NNNN 的序號來自 Step A 的擷取順序，序號大的視為較新。
        self._mails.sort(key=lambda m: (m.sent_at, m.mail_id), reverse=True)
        self._mail_index = {m.mail_id: m for m in self._mails}

        # ---- 系統事件 ----
        self._alerts = self._build_alerts(raw_summaries, raw_mails)

        # ---- 今日重點 ----
        self._brief = self._build_daily_brief(digest_texts)

        self._loaded_at = datetime.now()

    def _read_json(self, path: Path) -> Dict[str, Any]:
        """讀單一 JSON。單檔損毀不影響其他郵件。"""
        try:
            with path.open("r", encoding="utf-8") as fp:
                data = json.load(fp)
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _build_asset_url(self, mail_id: str, filename: str) -> str:
        """組出內嵌圖片的可存取 URL。

        圖片實際位於 REAL_DATA_DIR 底下，不在 assets/，
        由 app/main.py 掛的靜態路由提供。
        """
        if not filename:
            return ""
        rel_dir = self._mail_dirs.get(mail_id, "")
        if not rel_dir:
            return ""
        return f"{config.REAL_ASSET_ROUTE}/{rel_dir}/{filename}"

    # ------------------------------------------------------------------
    # 系統事件
    # ------------------------------------------------------------------
    def _build_alerts(
        self,
        raw_summaries: Dict[str, Dict[str, Any]],
        raw_mails: Dict[str, Dict[str, Any]],
    ) -> List[SystemAlert]:
        """從 machine_alert 郵件推導系統事件。

        公司資料沒有獨立的告警檔，事件就是那些 machine_alert 郵件。
        重複的固定格式告警會依 alert_key 聚合（實測 52 封 → 31 組），
        避免事件頁被同一種告警灌滿。
        """
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for mail_id, summary in raw_summaries.items():
            if summary.get("category") != "machine_alert":
                continue
            key = str(summary.get("alert_key") or summary.get("subject") or mail_id)
            groups.setdefault(key, []).append(summary)

        alerts: List[SystemAlert] = []
        for members in groups.values():
            # 以序號最大（最新）的那封當代表。
            representative = max(members, key=lambda s: str(s.get("mail_id", "")))
            mail_id = str(representative.get("mail_id", ""))
            occurred = str((raw_mails.get(mail_id) or {}).get("date", ""))
            alerts.append(
                self._adapter.to_alert(
                    representative,
                    occurred_at_iso=occurred,
                    occurrence_count=len(members),
                )
            )

        # 嚴重的排前面，同級再依出現次數多的排前面。
        severity_rank = {"critical": 0, "warning": 1, "info": 2, "resolved": 3}
        alerts.sort(
            key=lambda a: (severity_rank.get(a.severity, 9), -a.occurrence_count)
        )
        return alerts

    # ------------------------------------------------------------------
    # 今日重點
    # ------------------------------------------------------------------
    def _build_daily_brief(self, digest_texts: List[str]) -> DailyBrief:
        """合成 AI 今日重點。

        公司 pipeline 沒有「今日重點」這個等價欄位，
        但有 Step D 產出的 daily_digest.md，以及已分類好的郵件。
        因此完整內容用 digest 原文，條列則由需處理郵件與嚴重告警合成。
        """
        highlights: List[BriefHighlight] = []

        action_mails = [
            m
            for m in self._mails
            if m.ai.action_required and m.ai.category != MailCategory.ALERT
        ]
        action_mails.sort(key=lambda m: -m.ai.importance)

        for mail in action_mails[:3]:
            highlights.append(
                BriefHighlight(
                    index=len(highlights) + 1,
                    text=f"{mail.sender.name}：{mail.subject}",
                    severity="warning" if mail.ai.importance >= 4 else "info",
                    mail_id=mail.mail_id,
                )
            )

        critical = [a for a in self._alerts if a.severity == "critical"]
        if critical:
            equipment = "、".join(a.equipment for a in critical[:3])
            highlights.append(
                BriefHighlight(
                    index=len(highlights) + 1,
                    text=f"{len(critical)} 台關鍵機台汙染因子超標：{equipment}",
                    severity="critical",
                    mail_id=critical[0].related_mail_id,
                )
            )

        total_alerts = sum(a.occurrence_count for a in self._alerts)
        if total_alerts:
            highlights.append(
                BriefHighlight(
                    index=len(highlights) + 1,
                    text=(
                        f"共 {total_alerts} 封系統告警，"
                        f"聚合為 {len(self._alerts)} 類事件"
                    ),
                    severity="info",
                    mail_id="",
                )
            )

        return DailyBrief(
            generated_at_label=fmt_datetime_label(self._loaded_at),
            headline=(
                f"今天主要有 {len(highlights)} 件需要關注："
                if highlights
                else "今天沒有需要特別關注的事項。"
            ),
            highlights=highlights[:_BRIEF_LIMIT],
            full_text="\n\n".join(digest_texts) or "（本批次沒有 daily_digest.md）",
            model_name="Qwen3.6-35B-A3B",
        )

    # ==================================================================
    # BaseMailRepository 介面
    # ==================================================================
    def get_all_mails(self) -> List[Mail]:
        return list(self._mails)

    def get_mail(self, mail_id: str) -> Optional[Mail]:
        return self._mail_index.get(mail_id)

    def get_ai_analysis(self, mail_id: str) -> Optional[AIAnalysis]:
        mail = self._mail_index.get(mail_id)
        return mail.ai if mail else None

    def get_system_alerts(self) -> List[SystemAlert]:
        return list(self._alerts)

    def get_daily_brief(self) -> DailyBrief:
        return self._brief

    def mark_as_read(self, mail_id: str) -> None:
        """標記已讀。

        目前只改記憶體狀態，不寫回 Lotus Notes。
        若之後要寫回，改這個方法即可，上層不受影響。
        """
        mail = self._mail_index.get(mail_id)
        if mail is not None:
            mail.is_read = True

    # ==================================================================
    # 診斷
    # ==================================================================
    def health_check(self) -> str:
        if self._load_error:
            return self._load_error
        return (
            f"OK — {self._selected_date} 共 {len(self._mails)} 封郵件 / "
            f"{len(self._alerts)} 類事件（{self._batch_count} 個批次資料夾）；"
            f"可選日期 {len(self.available_dates)} 天，來源：{self._data_dir}"
        )

    @property
    def last_update_label(self) -> str:
        return fmt_datetime_label(self._loaded_at)

    @property
    def reference_date(self) -> date:
        """目前檢視的日期就是這份資料的「今天」。

        pipeline 是按日期批次執行的，檢視 8/07 那批時，
        「今日總覽」要指 8/07，而不是系統當天。
        """
        return self._selected_date or self._today
