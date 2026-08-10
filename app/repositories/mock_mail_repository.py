"""Mock 資料來源實作。

讀 app/mock_data/*.json，經 MockMailAdapter 轉成內部 Model 後往上層送。

這個類別是「第一階段唯一啟用的 Repository」，
但它與 RealMailRepository 對上層而言完全等價：
兩者都只承諾 BaseMailRepository 定義的方法與回傳型別。

日期平移
--------
Mock JSON 內的日期以 config.MOCK_ANCHOR_DATE 為基準寫死。
開啟 config.MOCK_SHIFT_DATES 後，載入時會把所有日期整體平移到「執行當天」，
確保任何一天開啟 Demo，「今日總覽」都有資料。

這是 Mock Repository 的內部行為，Service / State / UI 完全不知道有這回事，
因此第二階段換成 RealMailRepository 時不會有任何殘留邏輯需要清除。
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from .. import config
from ..models import AIAnalysis, DailyBrief, Mail, SystemAlert
from ..utils import fmt_datetime_label, parse_iso, parse_iso_date
from .adapters import MockMailAdapter
from .base_mail_repository import BaseMailRepository


class MockMailRepository(BaseMailRepository):
    """以本機 JSON 檔為資料來源的 Repository。"""

    source_name = "Mock Data"

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        asset_prefix: Optional[str] = None,
        today: Optional[date] = None,
        shift_dates: Optional[bool] = None,
    ) -> None:
        self._data_dir = Path(data_dir or config.MOCK_DATA_DIR)
        self._asset_prefix = asset_prefix or config.ASSET_URL_PREFIX
        self._today = today or date.today()
        self._shift_dates = (
            config.MOCK_SHIFT_DATES if shift_dates is None else shift_dates
        )

        self._adapter = MockMailAdapter(
            today=self._today, asset_prefix=self._asset_prefix
        )

        # 載入後的內部模型
        self._mails: List[Mail] = []
        self._mail_index: Dict[str, Mail] = {}
        self._alerts: List[SystemAlert] = []
        self._brief: DailyBrief = DailyBrief()
        self._loaded_at: datetime = datetime.now()
        self._load_error: str = ""

        self.refresh()

    # ------------------------------------------------------------------
    # 載入
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        """重新讀取 JSON 並重建所有內部模型。"""
        self._load_error = ""
        try:
            raw_mails = self._read_json("mails.json")
            raw_analysis = self._read_json("analysis.json")
            raw_alerts = self._read_json("alerts.json")
            raw_dashboard = self._read_json("dashboard.json")
        except (OSError, json.JSONDecodeError) as exc:
            self._load_error = f"Mock 資料載入失敗：{exc}"
            self._mails = []
            self._mail_index = {}
            self._alerts = []
            self._brief = DailyBrief()
            self._loaded_at = datetime.now()
            return

        delta = self._shift_delta(raw_mails.get("_anchor_date", ""))

        mails_raw = [self._shift_mail(m, delta) for m in raw_mails.get("mails", [])]
        analyses_raw: Dict[str, Any] = {
            mail_id: self._shift_analysis(a, delta)
            for mail_id, a in (raw_analysis.get("analyses") or {}).items()
        }
        alerts_raw = [
            self._shift_alert(a, delta) for a in (raw_alerts.get("alerts") or [])
        ]

        self._mails = [
            self._adapter.to_mail(m, analyses_raw.get(str(m.get("mail_id", ""))))
            for m in mails_raw
        ]
        # 一律由新到舊，上層不需要自己排序。
        self._mails.sort(key=lambda m: m.sent_at, reverse=True)
        self._mail_index = {m.mail_id: m for m in self._mails}

        self._alerts = [self._adapter.to_alert(a) for a in alerts_raw]
        self._alerts.sort(key=lambda a: a.occurred_at, reverse=True)

        self._loaded_at = datetime.now()
        self._brief = self._adapter.to_daily_brief(
            raw_dashboard.get("daily_brief") or {},
            generated_at_label=fmt_datetime_label(self._loaded_at),
        )

    def _read_json(self, filename: str) -> Dict[str, Any]:
        path = self._data_dir / filename
        with path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        return data if isinstance(data, dict) else {}

    # ------------------------------------------------------------------
    # 日期平移（Mock 專用）
    # ------------------------------------------------------------------
    def _shift_delta(self, anchor_raw: str) -> timedelta:
        """計算要把 Mock 日期往後平移幾天。"""
        if not self._shift_dates:
            return timedelta(0)
        anchor = parse_iso_date(anchor_raw or config.MOCK_ANCHOR_DATE)
        if anchor is None:
            return timedelta(0)
        return timedelta(days=(self._today - anchor).days)

    @staticmethod
    def _shift_value(value: Any, delta: timedelta, date_only: bool) -> Any:
        """平移單一日期 / 時間字串，格式維持不變。"""
        if not value or not delta:
            return value
        dt = parse_iso(str(value))
        if dt is None:
            return value
        moved = dt + delta
        return moved.date().isoformat() if date_only else moved.isoformat(
            timespec="seconds"
        )

    def _shift_mail(self, raw: Dict[str, Any], delta: timedelta) -> Dict[str, Any]:
        if not delta:
            return raw
        out = dict(raw)
        out["datetime"] = self._shift_value(raw.get("datetime"), delta, False)
        return out

    def _shift_analysis(self, raw: Dict[str, Any], delta: timedelta) -> Dict[str, Any]:
        if not delta:
            return raw
        out = dict(raw)
        out["deadline"] = self._shift_value(raw.get("deadline"), delta, True)
        out["analyzed_at"] = self._shift_value(raw.get("analyzed_at"), delta, False)
        return out

    def _shift_alert(self, raw: Dict[str, Any], delta: timedelta) -> Dict[str, Any]:
        if not delta:
            return raw
        out = dict(raw)
        out["occurred_at"] = self._shift_value(raw.get("occurred_at"), delta, False)
        return out

    # ------------------------------------------------------------------
    # BaseMailRepository 介面
    # ------------------------------------------------------------------
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
        """Mock 階段只改記憶體狀態，不寫回任何檔案。"""
        mail = self._mail_index.get(mail_id)
        if mail is not None:
            mail.is_read = True

    # ------------------------------------------------------------------
    # 診斷
    # ------------------------------------------------------------------
    def health_check(self) -> str:
        if self._load_error:
            return self._load_error
        return (
            f"OK — {len(self._mails)} 封郵件 / {len(self._alerts)} 筆事件"
            f"（{fmt_datetime_label(self._loaded_at)} 載入）"
        )

    @property
    def last_update_label(self) -> str:
        """資料最後載入時間，Header 的 Last Update 使用。"""
        return fmt_datetime_label(self._loaded_at)
