"""Ask AI 頁。

底部的 Ask AI 輸入列在所有頁面都在，這一頁提供完整的問答紀錄。
"""

from __future__ import annotations

import reflex as rx

from ..components import (
    answer_block,
    card,
    empty_state,
    page_layout,
    page_title_bar,
    toolbar_button,
)
from ..states import AppState
from ..theme import C, S


def _intro() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.icon("sparkles", size=16, color=C.PURPLE),
            rx.text("可以這樣問", size="2", weight="bold", color=C.TEXT),
            spacing="2",
            align="center",
        ),
        rx.flex(
            rx.foreach(
                AppState.ask_suggestions,
                lambda q: rx.box(
                    rx.hstack(
                        rx.icon("message-circle-question", size=13, color=C.PURPLE),
                        rx.text(q, size="2", color=C.TEXT_SECONDARY),
                        spacing="2",
                        align="center",
                    ),
                    on_click=AppState.ask_suggested(q),
                    padding="9px 12px",
                    background=C.SURFACE,
                    border=f"1px solid {C.BORDER_STRONG}",
                    border_radius=S.RADIUS_SM,
                    cursor="pointer",
                    _hover={
                        "background": C.PURPLE_SOFT,
                        "border_color": C.PURPLE_BORDER,
                    },
                ),
            ),
            wrap="wrap",
            gap="8px",
            width="100%",
        ),
        rx.text(
            "第一階段以本機規則比對 Mock Data 回答，不會呼叫任何外部 LLM API；"
            "第二階段只需要把 config.AI_MODE 改成 'llm'，這一頁不需要修改。",
            size="1",
            color=C.TEXT_MUTED,
            line_height="1.7",
        ),
        spacing="3",
        width="100%",
        align="start",
    )


def ask_ai_page() -> rx.Component:
    return page_layout(
        page_title_bar(
            action=rx.cond(
                AppState.has_ask_history,
                toolbar_button(
                    "清除紀錄", icon="trash-2", on_click=AppState.clear_ask_history
                ),
                rx.fragment(),
            ),
        ),
        card(_intro()),
        rx.cond(
            AppState.has_ask_history,
            rx.vstack(
                rx.foreach(
                    AppState.ask_history,
                    lambda a: answer_block(a),
                ),
                spacing="3",
                width="100%",
            ),
            empty_state(
                "還沒有問答紀錄",
                "從下方的 Ask AI 輸入列開始提問",
                icon="message-circle",
            ),
        ),
    )
