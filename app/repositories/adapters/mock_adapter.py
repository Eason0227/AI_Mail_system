"""Mock JSON → 內部 Model 的轉換器。

刻意寫成獨立的 Adapter（而不是讓 Repository 直接建 Model），
是為了讓「公司環境接真實資料」時有現成的對照範本：
CompanyMailAdapter 只要輸出相同的 Model，上層完全不用改。

Mock JSON 的欄位名稱與內部 Model 刻意不同，例如：
    JSON  "type" / "content"   ->  Model  block_type / text
    JSON  "todos": ["文字", …]  ->  Model  List[TodoItem]
    JSON  "size": 428000        ->  Model  size_label = "418 KB"
用來驗證轉換層確實有發揮隔離作用。
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from ...models import (
    AIAnalysis,
    Attachment,
    BriefHighlight,
    ContentBlock,
    DailyBrief,
    KeyFact,
    Mail,
    MailCategory,
    Sender,
    Severity,
    SystemAlert,
    TodoItem,
    build_importance_stars,
    resolve_icon_key,
)
from ...utils import (
    days_until,
    fmt_date,
    fmt_datetime_label,
    fmt_day_label,
    fmt_list_time_label,
    fmt_size,
    fmt_time,
    initials_of,
    join_recipients,
    parse_iso,
    parse_iso_date,
    truncate,
)

_STATUS_LABELS = {
    "open": "處理中",
    "monitoring": "監控中",
    "resolved": "已解決",
    "closed": "已結案",
}


class MockMailAdapter:
    """把 Mock JSON 結構轉成內部 Model。

    Args:
        today: 計算「今天 / 昨天 / 距離期限幾天」的基準日。
        asset_prefix: 郵件圖片的 URL 前綴。
    """

    def __init__(self, today: date, asset_prefix: str = "/") -> None:
        self._today = today
        self._asset_prefix = asset_prefix

    # ------------------------------------------------------------------
    # Mail
    # ------------------------------------------------------------------
    def to_mail(
        self,
        raw: Dict[str, Any],
        raw_analysis: Optional[Dict[str, Any]] = None,
    ) -> Mail:
        """單封郵件的原始 dict → Mail。"""
        mail_id = str(raw.get("mail_id", ""))
        subject = str(raw.get("subject", ""))

        sender = self._to_sender(raw.get("sender") or {})
        blocks = [self._to_block(b) for b in (raw.get("content_blocks") or [])]
        attachments = [
            self._to_attachment(mail_id, i, a)
            for i, a in enumerate(raw.get("attachments") or [])
        ]

        dt = parse_iso(str(raw.get("datetime", "")))
        if dt is None:
            time_label = date_label = datetime_label = list_time = day_label = ""
            sent_at = ""
        else:
            sent_at = dt.isoformat(timespec="seconds")
            time_label = fmt_time(dt)
            date_label = fmt_date(dt)
            datetime_label = fmt_datetime_label(dt)
            list_time = fmt_list_time_label(dt, self._today)
            day_label = fmt_day_label(dt, self._today)

        to_list = [str(x) for x in (raw.get("to") or [])]
        cc_list = [str(x) for x in (raw.get("cc") or [])]

        analysis = self.to_analysis(mail_id, raw_analysis or {}, subject)

        return Mail(
            mail_id=mail_id,
            subject=subject,
            sender=sender,
            to=to_list,
            cc=cc_list,
            sent_at=sent_at,
            time_label=time_label,
            date_label=date_label,
            datetime_label=datetime_label,
            list_time_label=list_time,
            day_label=day_label,
            is_read=bool(raw.get("is_read", False)),
            has_attachment=bool(attachments),
            attachment_count=len(attachments),
            preview=self._build_preview(blocks),
            to_label=join_recipients(to_list),
            cc_label=join_recipients(cc_list),
            content_blocks=blocks,
            attachments=attachments,
            ai=analysis,
            source="Mock",
            folder=str(raw.get("folder", "Inbox")),
        )

    def _to_sender(self, raw: Dict[str, Any]) -> Sender:
        name = str(raw.get("name", ""))
        return Sender(
            name=name,
            email=str(raw.get("email", "")),
            initials=initials_of(name),
            is_key_person=bool(raw.get("key_person", False)),
            title=str(raw.get("title", "")),
        )

    def _to_block(self, raw: Dict[str, Any]) -> ContentBlock:
        """Mock JSON 的 content block → ContentBlock。

        注意欄位改名：JSON 用 type / content，Model 用 block_type / text。
        """
        block_type = str(raw.get("type", "text"))
        src = str(raw.get("src", ""))
        if src:
            src = self._asset_url(src)
        rows_raw = raw.get("rows") or []
        return ContentBlock(
            block_type=block_type,
            text=str(raw.get("content", "")),
            src=src,
            caption=str(raw.get("caption", "")),
            columns=[str(c) for c in (raw.get("columns") or [])],
            rows=[[str(cell) for cell in row] for row in rows_raw],
            # JSON 的 "items" -> Model 的 list_items（避開 Reflex Var 的保留方法名）
            list_items=[str(i) for i in (raw.get("items") or [])],
        )

    def _to_attachment(
        self, mail_id: str, index: int, raw: Dict[str, Any]
    ) -> Attachment:
        file_type = str(raw.get("type", ""))
        return Attachment(
            attachment_id=f"{mail_id}_ATT_{index + 1:02d}",
            filename=str(raw.get("filename", "")),
            file_type=file_type,
            size_label=fmt_size(raw.get("size", 0)),
            url="",
            is_inline=bool(raw.get("inline", False)),
            icon_key=resolve_icon_key(file_type),
            # Mock 階段沒有實體檔案，UI 會顯示為停用狀態。
            downloadable=False,
        )

    def _asset_url(self, src: str) -> str:
        """把 JSON 內的相對路徑轉成可用的 URL。"""
        if src.startswith(("http://", "https://", "/")):
            return src
        return f"{self._asset_prefix}{src.lstrip('/')}"

    def _build_preview(self, blocks: List[ContentBlock]) -> str:
        """取第一段有意義的文字作為 Mail List 的預覽。"""
        for block in blocks:
            if block.block_type == "text" and block.text.strip():
                text = block.text.strip()
                # 跳過系統郵件開頭的制式提示
                if text.startswith("***"):
                    continue
                return truncate(text, 80)
        for block in blocks:
            if block.block_type == "text" and block.text.strip():
                return truncate(block.text.strip(), 80)
        return ""

    # ------------------------------------------------------------------
    # AI Analysis
    # ------------------------------------------------------------------
    def to_analysis(
        self,
        mail_id: str,
        raw: Dict[str, Any],
        mail_subject: str = "",
    ) -> AIAnalysis:
        """LLM 結構化結果 dict → AIAnalysis。"""
        if not raw:
            return AIAnalysis(mail_id=mail_id)

        category = str(raw.get("category", MailCategory.INFO))
        importance = int(raw.get("importance", 0) or 0)

        deadline_raw = str(raw.get("deadline", "") or "")
        deadline_date = parse_iso_date(deadline_raw) if deadline_raw else None
        if deadline_date:
            days_left = days_until(deadline_date, self._today)
            deadline_label = fmt_date(deadline_date)
        else:
            days_left = 999
            deadline_label = ""

        todos = self._to_todos(mail_id, raw.get("todos") or [], mail_subject, deadline_label)

        confidence = float(raw.get("confidence", 0.0) or 0.0)

        return AIAnalysis(
            mail_id=mail_id,
            importance=importance,
            category=category,
            category_label=MailCategory.label(category),
            action_required=bool(raw.get("action_required", False)),
            deadline=deadline_date.isoformat() if deadline_date else "",
            deadline_label=deadline_label,
            deadline_days_left=days_left,
            has_deadline=deadline_date is not None,
            is_overdue=deadline_date is not None and days_left < 0,
            is_due_soon=deadline_date is not None and 0 <= days_left <= 3,
            summary=str(raw.get("summary", "")),
            todos=todos,
            recommendations=[str(r) for r in (raw.get("recommendations") or [])],
            key_facts=[self._to_key_fact(k) for k in (raw.get("key_facts") or [])],
            reply_draft=str(raw.get("reply_draft", "")),
            importance_stars=build_importance_stars(importance),
            has_analysis=bool(raw.get("summary")),
            model_name=str(raw.get("model", "mock-multimodal-llm-v1")),
            analyzed_at=str(raw.get("analyzed_at", "")),
            confidence=confidence,
            confidence_label=f"{confidence * 100:.0f}%" if confidence > 0 else "",
        )

    def _to_todos(
        self,
        mail_id: str,
        raw_todos: List[Any],
        mail_subject: str,
        deadline_label: str,
    ) -> List[TodoItem]:
        """待辦清單。

        Mock JSON 的 todos 是純字串陣列，這裡展開成完整的 TodoItem，
        補上來源郵件與期限，讓「待辦事項」頁面可以獨立顯示。
        """
        todos: List[TodoItem] = []
        for i, item in enumerate(raw_todos):
            if isinstance(item, dict):
                text = str(item.get("text", ""))
                done = bool(item.get("done", False))
                priority = str(item.get("priority", "normal"))
            else:
                text = str(item)
                done = False
                priority = "normal"
            if not text:
                continue
            todos.append(
                TodoItem(
                    todo_id=f"{mail_id}_TODO_{i + 1:02d}",
                    text=text,
                    done=done,
                    deadline_label=deadline_label,
                    priority=priority,
                    mail_id=mail_id,
                    mail_subject=mail_subject,
                )
            )
        return todos

    def _to_key_fact(self, raw: Dict[str, Any]) -> KeyFact:
        return KeyFact(
            label=str(raw.get("label", "")),
            value=str(raw.get("value", "")),
            emphasis=bool(raw.get("emphasis", False)),
        )

    # ------------------------------------------------------------------
    # System Alert
    # ------------------------------------------------------------------
    def to_alert(self, raw: Dict[str, Any]) -> SystemAlert:
        """告警 dict → SystemAlert。"""
        severity = str(raw.get("severity", Severity.WARNING))
        status = str(raw.get("status", "open"))
        dt = parse_iso(str(raw.get("occurred_at", "")))
        return SystemAlert(
            alert_id=str(raw.get("alert_id", "")),
            equipment=str(raw.get("equipment", "")),
            alert_type=str(raw.get("alert_type", "")),
            description=str(raw.get("description", "")),
            metric_label=str(raw.get("metric_label", "")),
            metric_value=str(raw.get("metric_value", "")),
            duration_label=str(raw.get("duration", "")),
            severity=severity,
            severity_label=Severity.label(severity),
            status=status,
            status_label=_STATUS_LABELS.get(status, status),
            occurred_at=dt.isoformat(timespec="seconds") if dt else "",
            occurred_at_label=fmt_datetime_label(dt) if dt else "",
            related_mail_id=str(raw.get("related_mail_id", "")),
            owner=str(raw.get("owner", "")),
        )

    # ------------------------------------------------------------------
    # Daily Brief
    # ------------------------------------------------------------------
    def to_daily_brief(self, raw: Dict[str, Any], generated_at_label: str) -> DailyBrief:
        """今日重點 dict → DailyBrief。"""
        highlights = []
        for i, h in enumerate(raw.get("highlights") or []):
            highlights.append(
                BriefHighlight(
                    index=i + 1,
                    text=str(h.get("text", "")),
                    severity=str(h.get("severity", "info")),
                    mail_id=str(h.get("mail_id", "")),
                )
            )
        return DailyBrief(
            generated_at_label=generated_at_label,
            headline=str(raw.get("headline", "")),
            highlights=highlights,
            full_text=str(raw.get("full_text", "")),
            model_name=str(raw.get("model", "")),
        )
