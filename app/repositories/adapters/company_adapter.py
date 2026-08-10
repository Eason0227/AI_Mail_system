"""公司 Structured JSON → 內部 Model。

對應的來源是 personal_assistant_v2 這條 pipeline 的輸出::

    Lotus Notes -> Step A -> mails/mail_NNNN/mail.json
                -> Step C -> summaries/mail_NNNN_summary.json

**所有格式差異都吸收在這一層**，Service / State / Component 不需要知道
公司 JSON 長什麼樣子。

實際 Schema 與 Mock 的主要差異
------------------------------
============  ==========================  ================================
內部 Model     公司欄位                     處理方式
==============  ==========================  ==============================
內部 Model       公司欄位                     處理方式
==============  ==========================  ==============================
sender          from（純字串，4 種格式）       _parse_sender() 解析
sent_at         date（只有日期，沒有時間）      補 00:00，time_label 留空
content_blocks  blocks（image 用 path）      欄位改名 + 組 URL
importance      priority（high/medium/low）  _to_importance() 三級轉五級
todos           action_items                 改名
key_facts       key_points（純字串陣列）       改放 AIAnalysis.key_points
category        7 種值域                      _CATEGORY_MAP
action_required reply_needed + category      綜合判定
deadline        deadline                     Step C 已保證是 YYYY-MM-DD 或空字串
recommendations recommendations              直接對應
reply_draft     reply_draft                  直接對應
==============  ==========================  ==============================

deadline / recommendations / reply_draft 是後來才加進 Step C 的 prompt，
舊批次的 summary.json 沒有這三個欄位，本層一律容錯成空值，
UI 會自動隱藏對應區塊，不需要回頭重跑舊資料。
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional

from ...models import (
    AIAnalysis,
    Attachment,
    ContentBlock,
    KeyFact,
    Mail,
    MailCategory,
    Sender,
    Severity,
    SystemAlert,
    TodoItem,
    build_importance_stars,
)
from ...utils import (
    days_until,
    fmt_date,
    fmt_day_label,
    fmt_list_time_label,
    initials_of,
    join_recipients,
    parse_iso,
    parse_iso_date,
    truncate,
)
from .alert_parser import parse_alert_subject, resolve_equipment, strip_security_tag

# --------------------------------------------------------------------------
# 對照表
# --------------------------------------------------------------------------
#: 公司 category → 內部 MailCategory。
_CATEGORY_MAP: Dict[str, str] = {
    "urgent": MailCategory.ACTION_REQUIRED,
    "action_required": MailCategory.ACTION_REQUIRED,
    "meeting": MailCategory.MEETING,
    "report": MailCategory.REPORT,
    "fyi": MailCategory.INFO,
    "machine_alert": MailCategory.ALERT,
    "junk": MailCategory.JUNK,
}

#: priority → 重要度基礎分。
_PRIORITY_BASE: Dict[str, int] = {"high": 5, "medium": 3, "low": 1}

#: addressed_to_me → 中文顯示。
_ADDRESSED_LABELS: Dict[str, str] = {
    "direct": "直接收件人",
    "cc": "僅副本",
    "broadcast": "群發",
    "unknown": "無法判定",
}

#: alert_type → 嚴重度（關鍵機台會再升一級，見 _alert_severity）。
_ALERT_SEVERITY: Dict[str, str] = {
    "汙染因子超標": Severity.WARNING,
    "裝置斷線/離線": Severity.WARNING,
    "自動派報": Severity.INFO,
    "其他系統告警": Severity.INFO,
}

#: 視為需要本人處理的公司分類。
_ACTION_CATEGORIES = ("urgent", "action_required")

#: from 欄位的解析樣式。
_ANGLE_EMAIL = re.compile(r'^\s*"?(?P<name>[^"<]*?)"?\s*<(?P<email>[^>]+)>\s*$')
_NOTES_DN = re.compile(r"^\s*CN=(?P<name>[^/]+)/")
_SHORT_DN = re.compile(r"^\s*(?P<name>[^/]+)/[A-Za-z0-9_]+/[A-Za-z0-9_]+\s*$")


class CompanyMailAdapter:
    """把公司 pipeline 的 JSON 轉成內部 Model。

    Args:
        today: 計算「今天 / 昨天」的基準日。
        asset_url_builder: 給定 (mail_id, 檔名) 回傳圖片可存取 URL 的函式。
        key_person_keywords: 命中即視為主管 / 關鍵窗口的寄件者關鍵字。
    """

    def __init__(
        self,
        today: date,
        asset_url_builder=None,
        key_person_keywords: Optional[List[str]] = None,
    ) -> None:
        self._today = today
        self._asset_url = asset_url_builder or (lambda mail_id, name: "")
        self._key_person_keywords = [
            k.strip().lower() for k in (key_person_keywords or []) if k.strip()
        ]

    # ==================================================================
    # Mail
    # ==================================================================
    def to_mail(
        self,
        raw: Dict[str, Any],
        raw_summary: Optional[Dict[str, Any]] = None,
    ) -> Mail:
        """mail.json (+ summary.json) → Mail。"""
        mail_id = str(raw.get("mail_id", ""))
        subject_raw = str(raw.get("subject", ""))
        subject = strip_security_tag(subject_raw)

        sender = self._parse_sender(str(raw.get("from", "")))
        blocks = [
            self._to_block(mail_id, b) for b in (raw.get("blocks") or [])
        ]

        to_list = [str(x) for x in (raw.get("to") or [])]
        cc_list = [str(x) for x in (raw.get("cc") or [])]

        # 公司資料只有日期沒有時間，補 00:00 讓排序與篩選可用，
        # 但 time_label 留空，避免在畫面上顯示不存在的「00:00」。
        dt = parse_iso(str(raw.get("date", "")))
        if dt is None:
            sent_at = date_label = datetime_label = list_time = day_label = ""
        else:
            sent_at = dt.isoformat(timespec="seconds")
            date_label = fmt_date(dt)
            datetime_label = date_label
            list_time = fmt_list_time_label(dt, self._today)
            day_label = fmt_day_label(dt, self._today)

        analysis = self.to_analysis(mail_id, raw_summary or {}, subject)

        return Mail(
            mail_id=mail_id,
            subject=subject,
            sender=sender,
            to=to_list,
            cc=cc_list,
            sent_at=sent_at,
            time_label="",
            date_label=date_label,
            datetime_label=datetime_label,
            list_time_label=list_time,
            day_label=day_label,
            # Lotus Notes 的已讀狀態目前沒有匯出，一律當未讀。
            is_read=False,
            has_attachment=False,
            attachment_count=0,
            preview=self._build_preview(blocks, analysis),
            to_label=join_recipients(to_list),
            cc_label=join_recipients(cc_list),
            content_blocks=blocks,
            attachments=[],
            ai=analysis,
            source="Lotus Notes",
            folder="Inbox",
        )

    # ------------------------------------------------------------------
    # 寄件者
    # ------------------------------------------------------------------
    def _parse_sender(self, raw: str) -> Sender:
        """解析 from 欄位。

        實際資料有四種格式（以下為示意值）::

            "Alert System" <alert-system@example.com>
            Alert System <alert-system@example.com>
            CN=Some User/OU=DEPT/O=ORG         （沒有 email）
            Some User/DEPT/ORG                 （沒有 email）
        """
        text = (raw or "").strip()
        name, email = text, ""

        m = _ANGLE_EMAIL.match(text)
        if m:
            name = m.group("name").strip() or m.group("email").split("@")[0]
            email = m.group("email").strip()
        else:
            m = _NOTES_DN.match(text) or _SHORT_DN.match(text)
            if m:
                name = m.group("name").strip()

        return Sender(
            name=name,
            email=email,
            initials=initials_of(name),
            is_key_person=self._is_key_person(name, email),
            title="",
        )

    def _is_key_person(self, name: str, email: str) -> bool:
        """依設定的關鍵字判斷是否為主管 / 關鍵窗口。"""
        if not self._key_person_keywords:
            return False
        haystack = f"{name} {email}".lower()
        return any(k in haystack for k in self._key_person_keywords)

    # ------------------------------------------------------------------
    # 內容區塊
    # ------------------------------------------------------------------
    def _to_block(self, mail_id: str, raw: Dict[str, Any]) -> ContentBlock:
        """公司 blocks → ContentBlock。

        圖片用 path（相對於該封信的資料夾）+ format，
        與 Mock 的 src 不同，在這裡組成可存取的 URL。
        """
        block_type = str(raw.get("type", "text"))
        if block_type == "image":
            return ContentBlock(
                block_type="image",
                src=self._asset_url(mail_id, str(raw.get("path", ""))),
                caption="",
            )
        return ContentBlock(
            block_type="text",
            text=str(raw.get("content", "")),
        )

    def _build_preview(self, blocks: List[ContentBlock], ai: AIAnalysis) -> str:
        """Mail List 的預覽文字。

        告警信的 blocks 是空的，改用 AI 摘要當預覽，
        否則清單上會是一整排空白。
        """
        for block in blocks:
            if block.block_type == "text" and block.text.strip():
                return truncate(block.text.strip(), 80)
        return truncate(ai.summary, 80)

    # ==================================================================
    # AI Analysis
    # ==================================================================
    def to_analysis(
        self,
        mail_id: str,
        raw: Dict[str, Any],
        mail_subject: str = "",
    ) -> AIAnalysis:
        """summary.json → AIAnalysis。"""
        if not raw:
            return AIAnalysis(mail_id=mail_id)

        company_category = str(raw.get("category", "fyi")).strip().lower()
        category = _CATEGORY_MAP.get(company_category, MailCategory.INFO)

        addressed = str(raw.get("addressed_to_me", "") or "").strip().lower()
        importance = self._to_importance(raw, company_category, addressed)

        action_required = bool(raw.get("reply_needed", False)) or (
            company_category in _ACTION_CATEGORIES
        )

        # deadline 由 Step C 的 validate_deadline() 保證是 YYYY-MM-DD 或空字串，
        # 但舊資料可能沒有這個欄位，因此仍然容錯處理。
        deadline_date = parse_iso_date(str(raw.get("deadline", "") or ""))
        if deadline_date is not None:
            days_left = days_until(deadline_date, self._today)
            deadline_label = fmt_date(deadline_date)
        else:
            days_left = 999
            deadline_label = ""

        todos = [
            TodoItem(
                todo_id=f"{mail_id}_TODO_{i + 1:02d}",
                text=str(text),
                done=False,
                deadline_label=deadline_label,
                priority=str(raw.get("priority", "normal")),
                mail_id=mail_id,
                mail_subject=mail_subject,
            )
            for i, text in enumerate(raw.get("action_items") or [])
            if str(text).strip()
        ]

        return AIAnalysis(
            mail_id=mail_id,
            importance=importance,
            category=category,
            category_label=MailCategory.label(category),
            action_required=action_required,
            deadline=deadline_date.isoformat() if deadline_date else "",
            deadline_label=deadline_label,
            deadline_days_left=days_left,
            has_deadline=deadline_date is not None,
            is_overdue=deadline_date is not None and days_left < 0,
            is_due_soon=deadline_date is not None and 0 <= days_left <= 3,
            recommendations=[
                str(r) for r in (raw.get("recommendations") or []) if str(r).strip()
            ],
            reply_draft=str(raw.get("reply_draft", "") or ""),
            # 公司 LLM 輸出的是 key_points（純字串），沒有 label/value 配對。
            key_facts=[],
            summary=str(raw.get("summary", "")),
            todos=todos,
            key_points=[str(k) for k in (raw.get("key_points") or [])],
            addressed_to=addressed,
            addressed_to_label=_ADDRESSED_LABELS.get(addressed, ""),
            importance_stars=build_importance_stars(importance),
            has_analysis=bool(raw.get("summary")),
            model_name="Qwen3.6-35B-A3B",
            analyzed_at="",
            confidence=0.0,
            confidence_label="",
        )

    @staticmethod
    def _to_importance(
        raw: Dict[str, Any], company_category: str, addressed: str
    ) -> int:
        """priority（三級）→ importance（五級）。

        單看 priority 會壓縮太多資訊（實際資料只有 low / medium 兩種值，
        全部都會落在 1 或 3 星，「重要郵件」永遠是 0 封）。
        因此再納入兩個公司端已經判定好的訊號：

            +1  分類是 urgent / action_required
            +1  本人是直接收件人（addressed_to_me == "direct"）

        這是三級轉五級的刻度換算，屬於格式差異，所以放在 Adapter。
        「幾星算重要」的門檻仍然由 MailService 決定。
        """
        score = _PRIORITY_BASE.get(str(raw.get("priority", "low")).lower(), 1)
        if company_category in _ACTION_CATEGORIES:
            score += 1
        if addressed == "direct":
            score += 1
        return max(1, min(5, score))

    # ==================================================================
    # System Alert
    # ==================================================================
    def to_alert(
        self,
        raw_summary: Dict[str, Any],
        occurred_at_iso: str,
        occurrence_count: int = 1,
    ) -> SystemAlert:
        """machine_alert 的 summary → SystemAlert。

        公司資料沒有獨立的告警檔，事件是從 machine_alert 郵件推導出來的。
        告警信的本文是空的，但主旨是固定格式，資訊由 alert_parser 取出。
        """
        mail_id = str(raw_summary.get("mail_id", ""))
        subject = str(raw_summary.get("subject", ""))
        alert_type = str(raw_summary.get("alert_type", "") or "系統告警")

        parsed = parse_alert_subject(subject)
        equipment = resolve_equipment(raw_summary.get("machine"), subject)

        dt = parse_iso(occurred_at_iso)
        severity = self._alert_severity(alert_type, parsed.is_critical)

        return SystemAlert(
            alert_id=mail_id,
            equipment=equipment or "—",
            alert_type=alert_type,
            description=strip_security_tag(subject),
            metric_label=parsed.metric_label or "狀態",
            metric_value=parsed.metric_value or parsed.status_text or "—",
            duration_label=parsed.status_text or "—",
            severity=severity,
            severity_label=Severity.label(severity),
            # Lotus Notes 端沒有結案狀態，一律視為未結案。
            status="open",
            status_label="處理中",
            occurred_at=dt.isoformat(timespec="seconds") if dt else "",
            occurred_at_label=fmt_date(dt) if dt else "",
            related_mail_id=mail_id,
            owner=parsed.area,
            occurrence_count=occurrence_count,
        )

    @staticmethod
    def _alert_severity(alert_type: str, is_critical: bool) -> str:
        """關鍵機台的汙染因子超標視為嚴重，其餘依類型對照。"""
        if is_critical:
            return Severity.CRITICAL
        return _ALERT_SEVERITY.get(alert_type, Severity.WARNING)
