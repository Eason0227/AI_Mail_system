"""AI 今日重點摘要。

整塊都是 AI 產生的內容，因此以紫色系與 AI 標記與原始郵件明確區隔。
"""

from __future__ import annotations

import reflex as rx

from ..models import BriefHighlight
from ..states import AppState
from ..theme import C, S
from .ui import ai_tag, severity_bg, severity_fg


def _highlight(item: BriefHighlight) -> rx.Component:
    """單條重點。可點擊跳到來源郵件。"""
    return rx.hstack(
        rx.center(
            rx.text(item.index, size="1", weight="bold", line_height="1"),
            color=severity_fg(item.severity),
            background=severity_bg(item.severity),
            border_radius=S.RADIUS_PILL,
            width="20px",
            height="20px",
            flex_shrink="0",
            margin_top="1px",
        ),
        rx.text(
            item.text,
            size="2",
            color=C.TEXT,
            line_height="1.65",
            flex="1",
        ),
        rx.cond(
            item.mail_id != "",
            rx.icon(
                "chevron-right",
                size=15,
                color=C.TEXT_MUTED,
                flex_shrink="0",
                margin_top="2px",
            ),
            rx.fragment(),
        ),
        spacing="3",
        align="start",
        width="100%",
        padding="8px 10px",
        border_radius=S.RADIUS_SM,
        cursor=rx.cond(item.mail_id != "", "pointer", "default"),
        on_click=AppState.open_mail_summary(item.mail_id),
        _hover={"background": C.SURFACE},
    )


def _full_brief_dialog() -> rx.Component:
    """完整 Daily Brief 對話框。"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(
                rx.hstack(
                    rx.icon("sparkles", size=16, color=C.PURPLE),
                    rx.text("AI 今日重點 — 完整 Daily Brief", size="3", weight="bold"),
                    spacing="2",
                    align="center",
                ),
            ),
            rx.dialog.description(
                rx.text(
                    AppState.brief.generated_at_label + "　產生",
                    size="1",
                    color=C.TEXT_MUTED,
                ),
            ),
            rx.box(
                rx.text(
                    AppState.brief.full_text,
                    size="2",
                    color=C.TEXT,
                    line_height="1.85",
                    white_space="pre-wrap",
                ),
                margin_top="12px",
                padding="14px",
                background=C.PURPLE_SOFT,
                border=f"1px solid {C.PURPLE_BORDER}",
                border_radius=S.RADIUS_SM,
                max_height="56vh",
                overflow_y="auto",
            ),
            rx.hstack(
                rx.text(
                    "本段內容由 AI 產生，非原始郵件內容。",
                    size="1",
                    color=C.TEXT_MUTED,
                ),
                rx.spacer(),
                rx.dialog.close(
                    rx.button(
                        "關閉",
                        size="2",
                        background=C.PRIMARY,
                        color=C.TEXT_INVERSE,
                        cursor="pointer",
                    ),
                ),
                width="100%",
                align="center",
                margin_top="14px",
            ),
            max_width="760px",
        ),
        open=AppState.brief_open,
        on_open_change=AppState.set_brief_open,
    )


def daily_brief() -> rx.Component:
    """AI 今日重點區塊。"""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon("sparkles", size=17, color=C.PURPLE),
                rx.text("AI 今日重點", size="3", weight="bold", color=C.TEXT),
                ai_tag(),
                rx.spacer(),
                rx.text(
                    AppState.brief.generated_at_label,
                    size="1",
                    color=C.TEXT_MUTED,
                ),
                spacing="2",
                align="center",
                width="100%",
            ),
            rx.text(
                AppState.brief.headline,
                size="2",
                weight="medium",
                color=C.TEXT_SECONDARY,
            ),
            rx.vstack(
                rx.foreach(AppState.brief.highlights, _highlight),
                spacing="1",
                width="100%",
            ),
            rx.hstack(
                rx.button(
                    rx.icon("file-text", size=14),
                    rx.text("查看完整 Daily Brief", size="1", weight="medium"),
                    on_click=AppState.open_brief,
                    color=C.PURPLE,
                    background=C.SURFACE,
                    border=f"1px solid {C.PURPLE_BORDER}",
                    border_radius=S.RADIUS_SM,
                    height="30px",
                    padding="0 12px",
                    cursor="pointer",
                    _hover={"background": C.PURPLE_SOFT},
                ),
                rx.spacer(),
                rx.text(
                    AppState.brief.model_name,
                    size="1",
                    color=C.TEXT_MUTED,
                ),
                width="100%",
                align="center",
                margin_top="2px",
            ),
            spacing="3",
            width="100%",
            align="start",
        ),
        _full_brief_dialog(),
        width="100%",
        padding="16px",
        background=f"linear-gradient(180deg, {C.PURPLE_SOFT} 0%, {C.SURFACE} 62%)",
        border=f"1px solid {C.PURPLE_BORDER}",
        border_radius=S.RADIUS,
        box_shadow=S.SHADOW,
    )
