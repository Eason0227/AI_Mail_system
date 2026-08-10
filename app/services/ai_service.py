"""AI 相關業務邏輯：Ask AI 與回覆草稿。

架構重點
--------
Ask AI 的「引擎」被抽象成 BaseAskAIEngine，目前有兩個實作：

    MockRuleAskAIEngine  第一階段：本機規則比對 Mock Data，不呼叫任何 API
    LlmAskAIEngine       第二階段：呼叫公司端 LLM

UI 只認得 AskAIAnswer 這個結構，因此把 config.AI_MODE 從 "mock" 改成 "llm"
就能換掉整個回答來源，Ask AI 元件一行都不用改。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Tuple

from .. import config
from ..models import AskAIAnswer, AskAIReference, Mail
from ..utils import fmt_datetime_label, truncate
from .mail_service import MailService

#: Ask AI 輸入框下方顯示的建議問題。
SUGGESTED_QUESTIONS: List[str] = [
    "今天有哪些重要郵件？",
    "有哪些需要我處理？",
    "有哪些 Deadline？",
    "有哪些設備異常？",
]


class BaseAskAIEngine(ABC):
    """Ask AI 引擎介面。"""

    name: str = "unknown"

    @abstractmethod
    def answer(self, question: str) -> AskAIAnswer:
        """回答一個問題。"""


# --------------------------------------------------------------------------
# 第一階段：本機規則引擎
# --------------------------------------------------------------------------
class MockRuleAskAIEngine(BaseAskAIEngine):
    """以關鍵字比對 Mock Data 產生答案。

    刻意不呼叫任何外部 API：第一階段必須能完全離線展示。
    回傳結構與 LLM 版本完全相同，因此之後替換不影響 UI。
    """

    name = "mock-rule"

    def __init__(self, mail_service: MailService) -> None:
        self._mails = mail_service

    # -- 意圖比對 --------------------------------------------------------
    #: (關鍵字, 處理方法名稱)。由上往下比對，先命中先處理。
    _INTENTS: Tuple[Tuple[Tuple[str, ...], str], ...] = (
        (("設備", "機台", "異常", "告警", "alert", "oob", "particle"), "_answer_alerts"),
        (("deadline", "期限", "到期", "幾號前", "什麼時候要"), "_answer_deadlines"),
        (("待辦", "todo", "要做", "行動"), "_answer_todos"),
        (("處理", "回覆", "回信", "需要我", "action"), "_answer_actions"),
        (("重要", "important", "優先"), "_answer_important"),
        (("主管", "經理", "協理", "關鍵窗口"), "_answer_key_person"),
        (("報表", "report", "日報"), "_answer_reports"),
        (("總覽", "摘要", "重點", "今天", "概況"), "_answer_overview"),
    )

    def answer(self, question: str) -> AskAIAnswer:
        text = (question or "").strip()
        if not text:
            return self._not_matched(text)

        lowered = text.lower()
        for keywords, handler_name in self._INTENTS:
            if any(k in lowered for k in keywords):
                handler = getattr(self, handler_name)
                return handler(text)

        return self._not_matched(text)

    # -- 各意圖的回答 ----------------------------------------------------
    def _answer_important(self, question: str) -> AskAIAnswer:
        mails = self._mails.get_important_mails()
        if not mails:
            return self._build(question, "今天沒有重要度 4 星以上的郵件。")
        return self._build(
            question,
            f"目前有 {len(mails)} 封重要郵件，依重要度排列如下：",
            bullets=[
                f"{m.ai.importance_stars}　{m.sender.name}：{m.subject}"
                for m in sorted(mails, key=lambda x: -x.ai.importance)
            ],
            refs=mails,
            reason="重要度 4 星以上",
        )

    def _answer_actions(self, question: str) -> AskAIAnswer:
        mails = self._mails.get_action_items()
        if not mails:
            return self._build(question, "目前沒有需要您親自處理的郵件。")
        return self._build(
            question,
            f"有 {len(mails)} 封郵件需要您處理，已依急迫程度排序：",
            bullets=[self._action_line(m) for m in mails],
            refs=mails,
            reason="AI 判定需要本人處理",
        )

    def _answer_deadlines(self, question: str) -> AskAIAnswer:
        mails = self._mails.get_deadline_mails()
        if not mails:
            return self._build(question, "目前沒有帶期限的郵件。")
        overdue = [m for m in mails if m.ai.is_overdue]
        head = f"共有 {len(mails)} 項有期限的事項"
        head += f"，其中 {len(overdue)} 項已逾期：" if overdue else "："
        return self._build(
            question,
            head,
            bullets=[
                f"{m.ai.deadline_label}（{self._days_text(m)}）　{m.subject}"
                for m in mails
            ],
            refs=mails,
            reason="含 Deadline",
        )

    def _answer_todos(self, question: str) -> AskAIAnswer:
        todos = [t for t in self._mails.get_todos() if not t.done]
        if not todos:
            return self._build(question, "目前沒有未完成的待辦事項。")
        return self._build(
            question,
            f"AI 從郵件中拆解出 {len(todos)} 項待辦：",
            bullets=[
                f"{t.text}" + (f"（{t.deadline_label} 前）" if t.deadline_label else "")
                for t in todos
            ],
        )

    def _answer_alerts(self, question: str) -> AskAIAnswer:
        alerts = self._mails.get_system_alerts()
        active = [a for a in alerts if a.status in ("open", "monitoring")]
        if not active:
            return self._build(question, "目前沒有進行中的設備 / 系統事件。")
        return self._build(
            question,
            f"目前有 {len(active)} 件進行中的設備 / 系統事件：",
            bullets=[
                f"{a.equipment}　{a.alert_type}　{a.metric_label} {a.metric_value}"
                f"　已持續 {a.duration_label}（{a.severity_label}）"
                for a in active
            ],
            refs=[
                m
                for m in (
                    self._mails.get_mail(a.related_mail_id) for a in active
                )
                if m is not None
            ],
            reason="事件相關郵件",
        )

    def _answer_key_person(self, question: str) -> AskAIAnswer:
        mails = self._mails.get_key_person_mails()
        if not mails:
            return self._build(question, "目前沒有來自主管或關鍵窗口的郵件。")
        return self._build(
            question,
            f"有 {len(mails)} 封來自主管 / 關鍵窗口的郵件：",
            bullets=[
                f"{m.sender.name}（{m.sender.title}）：{m.subject}" for m in mails
            ],
            refs=mails,
            reason="寄件者為主管 / 關鍵窗口",
        )

    def _answer_reports(self, question: str) -> AskAIAnswer:
        mails = self._mails.get_report_mails()
        if not mails:
            return self._build(question, "目前沒有報表類郵件。")
        return self._build(
            question,
            f"共有 {len(mails)} 封報表類郵件：",
            bullets=[f"{m.list_time_label}　{m.subject}" for m in mails],
            refs=mails,
            reason="分類為報表",
        )

    def _answer_overview(self, question: str) -> AskAIAnswer:
        today = self._mails.get_today_mails()
        actions = self._mails.get_action_items()
        alerts = [
            a
            for a in self._mails.get_system_alerts()
            if a.status in ("open", "monitoring")
        ]
        todos = [t for t in self._mails.get_todos() if not t.done]

        bullets = [
            f"今天收到 {len(today)} 封郵件，其中 {sum(1 for m in today if not m.is_read)} 封未讀",
            f"{len(actions)} 封需要您處理",
            f"{len(todos)} 項待辦尚未完成",
            f"{len(alerts)} 件設備 / 系統事件進行中",
        ]
        if actions:
            bullets.append(f"最急的一件：{actions[0].subject}（{self._days_text(actions[0])}）")

        return self._build(
            question, "今天的整體概況如下：", bullets=bullets, refs=actions[:3],
            reason="今日需處理事項",
        )

    # -- 工具 ------------------------------------------------------------
    def _action_line(self, mail: Mail) -> str:
        parts = [mail.sender.name, mail.subject]
        if mail.ai.has_deadline:
            parts.append(f"{mail.ai.deadline_label} 前（{self._days_text(mail)}）")
        return "　".join(parts)

    @staticmethod
    def _days_text(mail: Mail) -> str:
        days = mail.ai.deadline_days_left
        if not mail.ai.has_deadline:
            return "無期限"
        if days < 0:
            return f"已逾期 {abs(days)} 天"
        if days == 0:
            return "今天到期"
        return f"剩 {days} 天"

    def _build(
        self,
        question: str,
        answer: str,
        bullets: Optional[List[str]] = None,
        refs: Optional[List[Mail]] = None,
        reason: str = "",
    ) -> AskAIAnswer:
        return AskAIAnswer(
            question=question,
            answer=answer,
            bullets=bullets or [],
            references=[self._to_reference(m, reason) for m in (refs or [])[:5]],
            engine=self.name,
            answered_at_label=fmt_datetime_label(datetime.now()),
            matched=True,
        )

    @staticmethod
    def _to_reference(mail: Mail, reason: str) -> AskAIReference:
        return AskAIReference(
            mail_id=mail.mail_id,
            subject=truncate(mail.subject, 40),
            sender_name=mail.sender.name,
            time_label=mail.list_time_label,
            reason=reason,
        )

    def _not_matched(self, question: str) -> AskAIAnswer:
        return AskAIAnswer(
            question=question,
            answer=(
                "目前的 Mock 版本還無法回答這個問題。"
                "第一階段以本機規則比對為主，可以試試下面幾種問法："
            ),
            bullets=list(SUGGESTED_QUESTIONS),
            engine=self.name,
            answered_at_label=fmt_datetime_label(datetime.now()),
            matched=False,
        )


# --------------------------------------------------------------------------
# 第二階段：LLM 引擎
# --------------------------------------------------------------------------
class LlmAskAIEngine(BaseAskAIEngine):
    """呼叫公司端 LLM 回答問題（第二階段）。

    **第一階段不啟用。** 保留這個類別是為了先把接點定義清楚：

    1. 用 MailService 取得與問題相關的郵件作為 context。
    2. 送給公司端 LLM。
    3. 把回應轉成 AskAIAnswer（含 references）。

    只要回傳 AskAIAnswer，Ask AI 元件完全不需要修改。
    """

    name = "llm"

    def __init__(self, mail_service: MailService) -> None:
        self._mails = mail_service

    def answer(self, question: str) -> AskAIAnswer:
        raise NotImplementedError(
            "LlmAskAIEngine 尚未實作。第二階段在公司環境接上 LLM 後再啟用，"
            "並把 config.AI_MODE 設為 'llm'。"
        )


# --------------------------------------------------------------------------
# Service
# --------------------------------------------------------------------------
class AskAIService:
    """Ask AI 對外入口。"""

    def __init__(
        self, mail_service: MailService, mode: Optional[str] = None
    ) -> None:
        self._mails = mail_service
        ai_mode = (mode or config.AI_MODE).strip().lower()
        self._engine: BaseAskAIEngine = (
            LlmAskAIEngine(mail_service)
            if ai_mode == "llm"
            else MockRuleAskAIEngine(mail_service)
        )

    @property
    def engine_name(self) -> str:
        return self._engine.name

    def suggested_questions(self) -> List[str]:
        return list(SUGGESTED_QUESTIONS)

    def ask(self, question: str) -> AskAIAnswer:
        """回答問題。引擎失敗時退回可顯示的錯誤，不讓 UI 崩掉。"""
        try:
            return self._engine.answer(question)
        except NotImplementedError as exc:
            return AskAIAnswer(
                question=question,
                answer=str(exc),
                engine=self._engine.name,
                answered_at_label=fmt_datetime_label(datetime.now()),
                matched=False,
            )

    # ------------------------------------------------------------------
    # 回覆草稿
    # ------------------------------------------------------------------
    def generate_reply_draft(self, mail_id: str) -> str:
        """產生回覆草稿。

        第一階段直接讀 Mock 的 reply_draft；
        第二階段改為呼叫 LLM，回傳型別不變（純文字）。

        注意：本系統不實作寄信，草稿只會停留在畫面上。
        """
        mail = self._mails.get_mail(mail_id)
        if mail is None:
            return ""
        return mail.ai.reply_draft
