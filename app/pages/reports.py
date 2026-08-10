"""報表 / Daily Report 頁。

報表本質上仍是郵件，因此直接沿用 Mail Workspace 的三欄版面，
差別只在 on_load 帶入的 nav key 是 NavKey.INBOX_REPORT
（要顯示哪些郵件由 MailService.get_mails_for_nav 決定）。
"""

from __future__ import annotations

import reflex as rx

from ..components import page_layout, page_title_bar
from .mail import mail_workspace


def reports_page() -> rx.Component:
    return page_layout(
        page_title_bar(),
        mail_workspace(),
        fill=True,
    )
