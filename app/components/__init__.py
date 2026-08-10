"""UI Component 層。

規則（對應需求第 29 條）：

* Component 不直接讀 JSON 檔，不知道檔案路徑。
* Component 不知道 Lotus Notes，也不知道 LLM。
* Component 只接受整理好的 Model / State。

因此第二階段替換資料來源時，這個目錄下的檔案完全不需要修改。
"""

from .action_card import action_card
from .ai_analysis import ai_analysis_panel
from .ask_ai import answer_block, ask_ai_bar
from .daily_brief import daily_brief
from .header import header
from .kpi_card import kpi_card, kpi_row
from .layout import page_layout, page_title_bar
from .mail_list import mail_list
from .mail_viewer import mail_viewer
from .sidebar import sidebar
from .system_alert import alert_card
from .todo_list import todo_checklist, todo_row
from .ui import (
    ai_tag,
    card,
    category_badge,
    deadline_badge,
    empty_state,
    panel,
    pill,
    section_header,
    severity_badge,
    toolbar_button,
)

__all__ = [
    "action_card",
    "ai_analysis_panel",
    "ai_tag",
    "alert_card",
    "answer_block",
    "ask_ai_bar",
    "card",
    "category_badge",
    "daily_brief",
    "deadline_badge",
    "empty_state",
    "header",
    "kpi_card",
    "kpi_row",
    "mail_list",
    "mail_viewer",
    "page_layout",
    "page_title_bar",
    "panel",
    "pill",
    "section_header",
    "severity_badge",
    "sidebar",
    "toolbar_button",
    "todo_checklist",
    "todo_row",
]
