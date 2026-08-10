"""頂部 Header。"""

from __future__ import annotations

import reflex as rx

from .. import config
from ..states import AppState
from ..theme import C, S
from .ui import pill


def _brand() -> rx.Component:
    return rx.hstack(
        rx.box(
            rx.icon("mails", size=18, color=C.TEXT_INVERSE),
            background=C.PRIMARY,
            border_radius=S.RADIUS_SM,
            padding="7px",
            display="flex",
        ),
        rx.vstack(
            rx.text(
                config.APP_TITLE,
                size="3",
                weight="bold",
                color=C.TEXT,
                line_height="1.2",
            ),
            rx.text(
                config.APP_SHORT_TITLE,
                size="1",
                color=C.TEXT_MUTED,
                line_height="1.2",
            ),
            spacing="0",
            align="start",
        ),
        # 開發階段的資料來源提示，正式版由 config.SHOW_MOCK_BADGE 自動關閉。
        rx.cond(
            AppState.show_mock_badge,
            pill(
                "MOCK DATA",
                fg=C.WARNING,
                bg=C.WARNING_SOFT,
                border=C.WARNING_BORDER,
                icon="flask-conical",
                margin_left="10px",
            ),
            rx.fragment(),
        ),
        spacing="3",
        align="center",
    )


def _date_picker() -> rx.Component:
    """檢視日期選擇器。

    資料來源沒有多天資料時（例如 Mock）available_dates 是空的，整個元件隱藏。
    """
    return rx.cond(
        AppState.available_dates.length() > 0,
        rx.hstack(
            rx.icon("calendar-days", size=14, color=C.TEXT_MUTED),
            rx.select(
                AppState.available_dates,
                value=AppState.selected_date,
                on_change=AppState.change_date,
                size="1",
            ),
            rx.cond(
                AppState.date_fallback_note != "",
                rx.tooltip(
                    rx.icon("info", size=13, color=C.WARNING),
                    content=AppState.date_fallback_note,
                ),
                rx.fragment(),
            ),
            spacing="2",
            align="center",
        ),
        rx.hstack(
            rx.icon("calendar-days", size=14, color=C.TEXT_MUTED),
            rx.text(AppState.today_label, size="2", color=C.TEXT_SECONDARY),
            spacing="2",
            align="center",
        ),
    )


def _meta() -> rx.Component:
    """日期與最後更新時間。"""
    return rx.hstack(
        _date_picker(),
        rx.box(width="1px", height="16px", background=C.BORDER),
        rx.hstack(
            rx.icon("history", size=14, color=C.TEXT_MUTED),
            rx.text("Last Update", size="1", color=C.TEXT_MUTED),
            rx.text(
                AppState.last_update_label,
                size="2",
                color=C.TEXT_SECONDARY,
            ),
            spacing="2",
            align="center",
        ),
        spacing="3",
        align="center",
    )


def _refresh_button() -> rx.Component:
    return rx.button(
        rx.cond(
            AppState.is_refreshing,
            rx.spinner(size="1"),
            rx.icon("refresh-cw", size=14),
        ),
        rx.text("更新郵件", size="1", weight="medium"),
        on_click=AppState.refresh_mails,
        disabled=AppState.is_refreshing,
        color=C.TEXT_INVERSE,
        background=C.PRIMARY,
        border_radius=S.RADIUS_SM,
        height="32px",
        padding="0 12px",
        cursor="pointer",
        _hover={"background": C.PRIMARY_HOVER},
    )


def _notification() -> rx.Component:
    """通知鈴鐺；紅點數量取自需要處理的郵件數。"""
    return rx.box(
        rx.icon("bell", size=17, color=C.TEXT_SECONDARY),
        rx.cond(
            AppState.nav_counts["action"] > 0,
            rx.box(
                rx.text(
                    AppState.nav_counts["action"],
                    size="1",
                    color=C.TEXT_INVERSE,
                    weight="bold",
                    line_height="1",
                ),
                position="absolute",
                top="-4px",
                right="-6px",
                background=C.DANGER,
                border_radius=S.RADIUS_PILL,
                min_width="16px",
                height="16px",
                display="flex",
                align_items="center",
                justify_content="center",
                padding="0 4px",
            ),
            rx.fragment(),
        ),
        position="relative",
        display="flex",
        cursor="pointer",
        padding="4px",
    )


def _user() -> rx.Component:
    user = config.CURRENT_USER
    return rx.hstack(
        rx.center(
            rx.text(
                user.get("initials", "U"),
                size="2",
                weight="bold",
                color=C.TEXT_INVERSE,
            ),
            background=C.PRIMARY,
            border_radius=S.RADIUS_PILL,
            width="32px",
            height="32px",
            flex_shrink="0",
        ),
        rx.vstack(
            rx.text(
                user.get("name", ""),
                size="2",
                weight="medium",
                color=C.TEXT,
                line_height="1.2",
            ),
            rx.text(
                user.get("role", ""),
                size="1",
                color=C.TEXT_MUTED,
                line_height="1.2",
            ),
            spacing="0",
            align="start",
        ),
        spacing="2",
        align="center",
    )


def header() -> rx.Component:
    """固定在最上方的 Header。"""
    return rx.hstack(
        _brand(),
        rx.spacer(),
        _meta(),
        rx.box(width="1px", height="20px", background=C.BORDER),
        _refresh_button(),
        _notification(),
        rx.box(width="1px", height="20px", background=C.BORDER),
        _user(),
        spacing="4",
        align="center",
        width="100%",
        height=S.HEADER_H,
        padding="0 20px",
        background=C.HEADER_BG,
        border_bottom=f"1px solid {C.BORDER}",
        box_shadow=S.SHADOW_HEADER,
        position="fixed",
        top="0",
        left="0",
        right="0",
        z_index="30",
    )
