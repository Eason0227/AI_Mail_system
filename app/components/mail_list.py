"""Mail List（三欄工作區左欄，25%）。

這是原始 Lotus Notes 郵件的 UI 呈現。
第一階段顯示 Mock Mail，第二階段顯示實際郵件，元件本身不需要修改。
"""

from __future__ import annotations

import reflex as rx

from ..models import Mail, MailFilter
from ..states import AppState
from ..theme import C, S
from .ui import empty_state, panel


def _search_box() -> rx.Component:
    return rx.hstack(
        rx.icon("search", size=15, color=C.TEXT_MUTED, flex_shrink="0"),
        rx.input(
            value=AppState.search_text,
            on_change=AppState.on_search_change,
            placeholder="搜尋主旨、寄件者、內文…",
            size="2",
            flex="1",
            variant="soft",
            background="transparent",
            border="none",
            outline="none",
            box_shadow="none",
            height="30px",
        ),
        rx.cond(
            AppState.search_text != "",
            rx.icon(
                "x",
                size=14,
                color=C.TEXT_MUTED,
                cursor="pointer",
                on_click=AppState.clear_search,
                flex_shrink="0",
            ),
            rx.fragment(),
        ),
        spacing="2",
        align="center",
        width="100%",
        padding="0 10px",
        background=C.BG_SUBTLE,
        border=f"1px solid {C.BORDER}",
        border_radius=S.RADIUS_SM,
    )


def _filter_tabs() -> rx.Component:
    """All / 重要 / 需處理 / 告警 / 報表。"""

    def tab(key: str) -> rx.Component:
        active = AppState.mail_filter == key
        return rx.box(
            rx.text(
                MailFilter.LABELS[key],
                size="1",
                weight=rx.cond(active, "bold", "regular"),
                color=rx.cond(active, C.TEXT_INVERSE, C.TEXT_SECONDARY),
                line_height="1",
                white_space="nowrap",
            ),
            on_click=AppState.set_filter(key),
            padding="5px 10px",
            border_radius=S.RADIUS_PILL,
            background=rx.cond(active, C.PRIMARY, "transparent"),
            cursor="pointer",
            _hover={"background": rx.cond(active, C.PRIMARY, C.BG_SUBTLE)},
        )

    return rx.hstack(
        *[tab(key) for key in MailFilter.ORDER],
        spacing="1",
        align="center",
        width="100%",
        wrap="wrap",
    )


def _flags(mail: Mail) -> rx.Component:
    """郵件狀態小圖示：重要 / 需處理 / 附件。"""
    return rx.hstack(
        rx.cond(
            mail.ai.importance >= 4,
            rx.icon("star", size=12, color=C.STAR, fill=C.STAR),
            rx.fragment(),
        ),
        rx.cond(
            mail.ai.action_required,
            rx.icon("circle-alert", size=12, color=C.DANGER),
            rx.fragment(),
        ),
        rx.cond(
            mail.has_attachment,
            rx.hstack(
                rx.icon("paperclip", size=12, color=C.TEXT_MUTED),
                rx.text(mail.attachment_count, size="1", color=C.TEXT_MUTED),
                spacing="0",
                align="center",
            ),
            rx.fragment(),
        ),
        spacing="1",
        align="center",
        flex_shrink="0",
    )


def _mail_row(mail: Mail) -> rx.Component:
    """清單中的一列郵件。"""
    selected = AppState.selected_mail.mail_id == mail.mail_id

    return rx.box(
        rx.hstack(
            # 未讀指示
            rx.box(
                width="6px",
                height="6px",
                border_radius=S.RADIUS_PILL,
                background=rx.cond(mail.is_read, "transparent", C.PRIMARY),
                flex_shrink="0",
                margin_top="6px",
            ),
            rx.vstack(
                rx.hstack(
                    rx.text(
                        mail.sender.name,
                        size="2",
                        weight=rx.cond(mail.is_read, "regular", "bold"),
                        color=C.TEXT,
                        overflow="hidden",
                        text_overflow="ellipsis",
                        white_space="nowrap",
                    ),
                    rx.cond(
                        mail.sender.is_key_person,
                        rx.icon("badge-check", size=12, color=C.PRIMARY),
                        rx.fragment(),
                    ),
                    rx.spacer(),
                    rx.text(
                        mail.list_time_label,
                        size="1",
                        color=C.TEXT_MUTED,
                        flex_shrink="0",
                    ),
                    spacing="1",
                    align="center",
                    width="100%",
                ),
                rx.text(
                    mail.subject,
                    size="2",
                    weight=rx.cond(mail.is_read, "regular", "medium"),
                    color=C.TEXT,
                    line_height="1.4",
                    overflow="hidden",
                    text_overflow="ellipsis",
                    display="-webkit-box",
                    style={"-webkit-line-clamp": "2", "-webkit-box-orient": "vertical"},
                ),
                rx.text(
                    mail.preview,
                    size="1",
                    color=C.TEXT_MUTED,
                    line_height="1.4",
                    overflow="hidden",
                    text_overflow="ellipsis",
                    white_space="nowrap",
                ),
                rx.hstack(
                    rx.box(
                        rx.text(
                            mail.ai.category_label,
                            size="1",
                            line_height="1",
                        ),
                        color=C.TEXT_SECONDARY,
                        background=C.BG_SUBTLE,
                        border_radius=S.RADIUS_PILL,
                        padding="2px 7px",
                    ),
                    rx.spacer(),
                    _flags(mail),
                    spacing="1",
                    align="center",
                    width="100%",
                ),
                spacing="1",
                align="start",
                flex="1",
                min_width="0",
            ),
            spacing="2",
            align="start",
            width="100%",
        ),
        on_click=AppState.select_mail(mail.mail_id),
        padding="10px 12px",
        cursor="pointer",
        border_bottom=f"1px solid {C.BORDER}",
        border_left="3px solid",
        border_left_color=rx.cond(selected, C.PRIMARY, "transparent"),
        background=rx.cond(selected, C.PRIMARY_SOFT, "transparent"),
        _hover={"background": rx.cond(selected, C.PRIMARY_SOFT, C.SURFACE_ALT)},
    )


def mail_list() -> rx.Component:
    """左欄：搜尋 + Filter + 郵件清單。"""
    return panel(
        rx.vstack(
            _search_box(),
            _filter_tabs(),
            rx.hstack(
                rx.text(
                    f"{AppState.visible_mail_count} 封郵件",
                    size="1",
                    color=C.TEXT_MUTED,
                ),
                rx.spacer(),
                rx.text("由新到舊", size="1", color=C.TEXT_MUTED),
                width="100%",
                align="center",
            ),
            spacing="2",
            width="100%",
            padding="12px",
            border_bottom=f"1px solid {C.BORDER}",
            flex_shrink="0",
        ),
        rx.cond(
            AppState.has_mails,
            rx.box(
                rx.foreach(AppState.visible_mails, _mail_row),
                flex="1",
                overflow_y="auto",
                min_height="0",
            ),
            empty_state(
                "沒有符合條件的郵件",
                "試著清除搜尋字串或切換 Filter",
                icon="mail-x",
                height="100%",
            ),
        ),
        flex="1",
        min_width="0",
        height="100%",
    )
