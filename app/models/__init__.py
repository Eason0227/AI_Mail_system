"""內部資料模型。

整個系統的「共同語言」。UI / State / Service 一律只認得這裡的型別。
任何外部資料來源（Mock JSON、Lotus Notes、公司 LLM JSON）都必須
先被 Adapter 轉換成這些模型，才能往上層傳。
"""

from .ai_analysis import AIAnalysis, KeyFact, TodoItem, build_importance_stars
from .ask_ai import AskAIAnswer, AskAIReference
from .attachment import Attachment, resolve_icon_key
from .dashboard import (
    BriefHighlight,
    DailyBrief,
    DashboardSummary,
    KpiSummary,
    SystemAlert,
)
from .enums import BlockType, MailCategory, MailFilter, NavKey, Severity
from .mail import EMPTY_MAIL, ContentBlock, Mail, Sender

__all__ = [
    "EMPTY_MAIL",
    "AIAnalysis",
    "AskAIAnswer",
    "AskAIReference",
    "Attachment",
    "BlockType",
    "BriefHighlight",
    "ContentBlock",
    "DailyBrief",
    "DashboardSummary",
    "KeyFact",
    "KpiSummary",
    "Mail",
    "MailCategory",
    "MailFilter",
    "NavKey",
    "Sender",
    "Severity",
    "SystemAlert",
    "TodoItem",
    "build_importance_stars",
    "resolve_icon_key",
]
