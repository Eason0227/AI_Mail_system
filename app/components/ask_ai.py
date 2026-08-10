"""Ask AI：底部固定輸入列與回答面板。

第一階段的答案由 MockRuleAskAIEngine 以規則比對 Mock Data 產生，
但這個元件只認得 AskAIAnswer，因此第二階段接上 LLM 後不需要修改。
"""

from __future__ import annotations

import reflex as rx

from ..models import AskAIAnswer, AskAIReference
from ..states import AppState
from ..theme import C, S
from .ui import ai_tag, toolbar_button


def _reference(ref: AskAIReference) -> rx.Component:
    """答案引用的來源郵件（可點擊開啟）。"""
    return rx.hstack(
        rx.icon("mail", size=13, color=C.PRIMARY, flex_shrink="0"),
        rx.text(ref.subject, size="1", color=C.PRIMARY, weight="medium"),
        rx.text(ref.sender_name, size="1", color=C.TEXT_MUTED),
        rx.text(ref.time_label, size="1", color=C.TEXT_MUTED),
        spacing="2",
        align="center",
        padding="5px 9px",
        background=C.PRIMARY_SOFT,
        border=f"1px solid {C.PRIMARY_BORDER}",
        border_radius=S.RADIUS_SM,
        cursor="pointer",
        on_click=AppState.open_mail_summary(ref.mail_id),
        _hover={"background": C.SURFACE},
    )


def answer_block(answer: AskAIAnswer, compact: bool = False) -> rx.Component:
    """單則回答。Ask AI 頁與底部面板共用。"""
    return rx.vstack(
        rx.hstack(
            rx.icon("message-circle-question", size=14, color=C.TEXT_MUTED),
            rx.text(answer.question, size="2", weight="bold", color=C.TEXT),
            rx.spacer(),
            rx.text(answer.answered_at_label, size="1", color=C.TEXT_MUTED),
            spacing="2",
            align="center",
            width="100%",
        ),
        rx.box(height="1px", background=C.BORDER, width="100%"),
        rx.hstack(
            ai_tag("AI 回答"),
            rx.text(f"引擎：{answer.engine}", size="1", color=C.TEXT_MUTED),
            rx.cond(
                ~answer.matched,
                rx.text("未能理解問題", size="1", color=C.WARNING),
                rx.fragment(),
            ),
            spacing="2",
            align="center",
        ),
        rx.text(answer.answer, size="2", color=C.TEXT, line_height="1.7"),
        rx.cond(
            answer.bullets.length() > 0,
            rx.vstack(
                rx.foreach(
                    answer.bullets,
                    lambda b: rx.hstack(
                        rx.box(
                            width="5px",
                            height="5px",
                            border_radius=S.RADIUS_PILL,
                            background=C.PURPLE,
                            margin_top="7px",
                            flex_shrink="0",
                        ),
                        rx.text(b, size="2", color=C.TEXT_SECONDARY, line_height="1.6"),
                        spacing="2",
                        align="start",
                        width="100%",
                    ),
                ),
                spacing="1",
                width="100%",
                padding_left="2px",
            ),
            rx.fragment(),
        ),
        rx.cond(
            answer.references.length() > 0,
            rx.vstack(
                rx.text("引用來源", size="1", color=C.TEXT_MUTED, weight="medium"),
                rx.flex(
                    rx.foreach(answer.references, _reference),
                    wrap="wrap",
                    gap="6px",
                ),
                spacing="2",
                align="start",
                width="100%",
                margin_top="4px",
            ),
            rx.fragment(),
        ),
        spacing="2",
        align="start",
        width="100%",
        padding="14px" if not compact else "12px",
        background=C.SURFACE,
        border=f"1px solid {C.PURPLE_BORDER}",
        border_left=f"3px solid {C.PURPLE}",
        border_radius=S.RADIUS,
    )


def _suggestions() -> rx.Component:
    """建議問題 chips。"""
    return rx.hstack(
        rx.foreach(
            AppState.ask_suggestions,
            lambda q: rx.box(
                rx.text(q, size="1", color=C.TEXT_SECONDARY),
                on_click=AppState.ask_suggested(q),
                padding="4px 10px",
                background=C.SURFACE,
                border=f"1px solid {C.BORDER_STRONG}",
                border_radius=S.RADIUS_PILL,
                cursor="pointer",
                white_space="nowrap",
                _hover={
                    "background": C.PRIMARY_SOFT,
                    "border_color": C.PRIMARY_BORDER,
                    "color": C.PRIMARY,
                },
            ),
        ),
        spacing="2",
        align="center",
        overflow_x="auto",
    )


def _answer_panel() -> rx.Component:
    """輸入列上方彈出的回答面板。"""
    return rx.cond(
        AppState.ask_panel_open,
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.text("Ask AI", size="2", weight="bold", color=C.TEXT),
                    rx.spacer(),
                    rx.link(
                        rx.text("開啟完整頁面", size="1", color=C.PRIMARY),
                        href="/ask-ai",
                        text_decoration="none",
                    ),
                    rx.icon(
                        "x",
                        size=15,
                        color=C.TEXT_MUTED,
                        cursor="pointer",
                        on_click=AppState.close_ask_panel,
                    ),
                    spacing="3",
                    align="center",
                    width="100%",
                ),
                rx.cond(
                    AppState.ask_loading,
                    rx.hstack(
                        rx.spinner(size="2"),
                        rx.text("AI 分析中…", size="2", color=C.TEXT_SECONDARY),
                        spacing="2",
                        align="center",
                        padding="14px",
                    ),
                    rx.cond(
                        AppState.has_ask_answer,
                        answer_block(AppState.ask_answer, compact=True),
                        rx.fragment(),
                    ),
                ),
                spacing="2",
                width="100%",
                align="start",
            ),
            position="absolute",
            bottom=S.ASKAI_H,
            left="0",
            right="0",
            max_height="52vh",
            overflow_y="auto",
            padding="12px 20px",
            background=C.BG,
            border_top=f"1px solid {C.BORDER}",
        ),
        rx.fragment(),
    )


def ask_ai_bar() -> rx.Component:
    """固定在畫面底部的 Ask AI 輸入列。"""
    return rx.box(
        _answer_panel(),
        rx.hstack(
            rx.icon("sparkles", size=16, color=C.PURPLE, flex_shrink="0"),
            rx.input(
                value=AppState.ask_input,
                on_change=AppState.on_ask_change,
                placeholder="Ask AI，例如：今天有哪些事情需要我回覆？",
                on_key_down=lambda key: rx.cond(key == "Enter", AppState.ask, rx.noop()),
                size="2",
                flex="1",
                background=C.SURFACE,
                border=f"1px solid {C.BORDER_STRONG}",
                border_radius=S.RADIUS_SM,
                height="36px",
            ),
            _suggestions(),
            rx.button(
                rx.cond(
                    AppState.ask_loading,
                    rx.spinner(size="1"),
                    rx.icon("send-horizontal", size=14),
                ),
                rx.text("送出", size="1", weight="medium"),
                on_click=AppState.ask,
                disabled=AppState.ask_loading,
                color=C.TEXT_INVERSE,
                background=C.PURPLE,
                border_radius=S.RADIUS_SM,
                height="36px",
                padding="0 14px",
                cursor="pointer",
                flex_shrink="0",
                _hover={"background": "#6B3ED8"},
            ),
            spacing="3",
            align="center",
            width="100%",
            height=S.ASKAI_H,
            padding="0 20px",
        ),
        position="fixed",
        bottom="0",
        left=S.SIDEBAR_W,
        right="0",
        background=C.SURFACE,
        border_top=f"1px solid {C.BORDER}",
        z_index="25",
    )
