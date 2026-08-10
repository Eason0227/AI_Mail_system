"""Mail Workspace：三欄式郵件工作區。

比例 25% / 45% / 30%：

    Mail List        原始郵件         AI Analysis
    （原始郵件清單）  （不含 AI 內容）  （全部為 AI 內容）

報表頁也共用同一個版面，差別只在 on_load 帶入的 nav key 不同。
"""

from __future__ import annotations

import reflex as rx

from ..components import (
    ai_analysis_panel,
    mail_list,
    mail_viewer,
    page_layout,
    page_title_bar,
)


def mail_workspace() -> rx.Component:
    """三欄工作區內容（不含頁面外框）。"""
    return rx.hstack(
        rx.box(mail_list(), width="25%", height="100%", min_width="0"),
        rx.box(mail_viewer(), width="45%", height="100%", min_width="0"),
        rx.box(ai_analysis_panel(), width="30%", height="100%", min_width="0"),
        spacing="3",
        width="100%",
        flex="1",
        min_height="0",
        align="stretch",
    )


def mail_page() -> rx.Component:
    """智慧收件匣 / 時間分類頁面。"""
    return page_layout(
        page_title_bar(),
        mail_workspace(),
        fill=True,
    )
