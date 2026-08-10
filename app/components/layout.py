"""頁面外框：Header + Sidebar + Main Content + 底部 Ask AI。

所有頁面都透過 page_layout() 產生，確保版面一致。
主要目標解析度 1920 × 1080。
"""

from __future__ import annotations

import reflex as rx

from ..states import AppState
from ..theme import C, S
from .ask_ai import ask_ai_bar
from .header import header
from .sidebar import sidebar

#: 主內容區的高度 = 視窗高 - Header - 底部 Ask AI。
_CONTENT_H = f"calc(100vh - {S.HEADER_H} - {S.ASKAI_H})"


def page_title_bar(action: rx.Component | None = None) -> rx.Component:
    """頁面標題列。標題文字來自 navigation.py，由 State 帶入。"""
    return rx.hstack(
        rx.vstack(
            rx.text(
                AppState.page_title,
                size="5",
                weight="bold",
                color=C.TEXT,
                line_height="1.3",
            ),
            rx.cond(
                AppState.page_subtitle != "",
                rx.text(AppState.page_subtitle, size="2", color=C.TEXT_MUTED),
                rx.fragment(),
            ),
            spacing="1",
            align="start",
        ),
        rx.spacer(),
        action if action is not None else rx.fragment(),
        width="100%",
        align="center",
        flex_shrink="0",
    )


def page_layout(*content, fill: bool = False) -> rx.Component:
    """組出完整頁面。

    Args:
        fill: True 代表內容自行填滿可視高度且不讓整頁捲動
              （Mail Workspace 這種三欄各自捲動的版面需要）。
    """
    main_style = {
        "margin_left": S.SIDEBAR_W,
        "margin_top": S.HEADER_H,
        "padding": S.PAGE_PAD,
        "background": C.BG,
    }
    if fill:
        main_style.update({"height": _CONTENT_H, "overflow": "hidden"})
    else:
        main_style.update({"min_height": _CONTENT_H, "padding_bottom": S.ASKAI_H})

    return rx.box(
        header(),
        sidebar(),
        rx.box(
            rx.vstack(
                *content,
                spacing="4",
                width="100%",
                height="100%" if fill else "auto",
                align="start",
            ),
            style=main_style,
        ),
        ask_ai_bar(),
        background=C.BG,
        min_height="100vh",
        width="100%",
    )
