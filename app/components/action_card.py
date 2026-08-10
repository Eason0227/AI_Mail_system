"""「需要您處理」卡片（首頁）。

每張卡顯示：寄件者 / 主旨 / 時間 / Deadline / AI 判定理由，
並提供 摘要、原信、AI 回覆 三個入口。
"""

from __future__ import annotations

import reflex as rx

from ..models import Mail
from ..states import AppState
from ..theme import C, S
from .ui import ai_tag, category_badge, deadline_badge, toolbar_button


def _avatar(mail: Mail) -> rx.Component:
    return rx.center(
        rx.text(
            mail.sender.initials,
            size="2",
            weight="bold",
            color=rx.cond(mail.sender.is_key_person, C.TEXT_INVERSE, C.TEXT_SECONDARY),
        ),
        background=rx.cond(mail.sender.is_key_person, C.PRIMARY, C.BG_SUBTLE),
        border_radius=S.RADIUS_PILL,
        width="34px",
        height="34px",
        flex_shrink="0",
    )


def action_card(mail: Mail) -> rx.Component:
    """單張需處理郵件卡。"""
    return rx.box(
        rx.vstack(
            # ---- 標題列 ----
            rx.hstack(
                _avatar(mail),
                rx.vstack(
                    rx.hstack(
                        rx.text(
                            mail.sender.name,
                            size="2",
                            weight="bold",
                            color=C.TEXT,
                        ),
                        rx.cond(
                            mail.sender.is_key_person,
                            rx.icon("badge-check", size=13, color=C.PRIMARY),
                            rx.fragment(),
                        ),
                        rx.text(mail.sender.title, size="1", color=C.TEXT_MUTED),
                        spacing="2",
                        align="center",
                    ),
                    rx.text(
                        mail.subject,
                        size="2",
                        weight="medium",
                        color=C.TEXT,
                        line_height="1.4",
                    ),
                    spacing="1",
                    align="start",
                    flex="1",
                    min_width="0",
                ),
                rx.vstack(
                    rx.text(mail.time_label, size="1", color=C.TEXT_MUTED),
                    rx.text(mail.day_label, size="1", color=C.TEXT_MUTED),
                    spacing="0",
                    align="end",
                    flex_shrink="0",
                ),
                spacing="3",
                align="start",
                width="100%",
            ),
            # ---- 標籤 ----
            rx.hstack(
                category_badge(mail.ai.category, mail.ai.category_label),
                deadline_badge(mail.ai),
                rx.text(
                    mail.ai.importance_stars,
                    size="1",
                    color=C.STAR,
                    letter_spacing="1px",
                ),
                spacing="2",
                align="center",
                wrap="wrap",
            ),
            # ---- AI 判定理由 ----
            rx.hstack(
                ai_tag("AI 判定"),
                rx.text(
                    mail.ai.summary,
                    size="1",
                    color=C.TEXT_SECONDARY,
                    line_height="1.6",
                    flex="1",
                ),
                spacing="2",
                align="start",
                width="100%",
                padding="9px 10px",
                background=C.PURPLE_SOFT,
                border_left=f"3px solid {C.PURPLE}",
                border_radius=S.RADIUS_SM,
            ),
            # ---- 動作 ----
            rx.hstack(
                toolbar_button(
                    "摘要",
                    icon="scan-text",
                    on_click=AppState.open_mail_summary(mail.mail_id),
                ),
                toolbar_button(
                    "原信",
                    icon="mail-open",
                    on_click=AppState.open_mail_original(mail.mail_id),
                ),
                toolbar_button(
                    "AI 回覆",
                    icon="reply",
                    variant="primary",
                    on_click=AppState.open_mail_reply(mail.mail_id),
                ),
                spacing="2",
                width="100%",
            ),
            spacing="3",
            width="100%",
            align="start",
        ),
        width="100%",
        padding="14px",
        background=C.SURFACE,
        border=f"1px solid {C.BORDER}",
        border_left=rx.cond(
            mail.ai.is_overdue,
            f"3px solid {C.DANGER}",
            rx.cond(
                mail.ai.is_due_soon,
                f"3px solid {C.WARNING}",
                f"3px solid {C.PRIMARY}",
            ),
        ),
        border_radius=S.RADIUS,
        box_shadow=S.SHADOW,
        transition="box-shadow .15s ease",
        _hover={"box_shadow": S.SHADOW_HOVER},
    )
