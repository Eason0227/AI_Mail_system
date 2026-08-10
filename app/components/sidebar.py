"""左側 Sidebar。

導覽內容來自 app/navigation.py，這裡只負責畫。
新增 / 調整導覽項目請改 navigation.py，不要改這個檔案。
"""

from __future__ import annotations

import reflex as rx

from ..navigation import NAV_GROUPS, SETTINGS_ITEM, NavItem
from ..states import AppState
from ..theme import C, S


def _counter(item: NavItem) -> rx.Component:
    """項目右側的數字。數字由 MailService 計算。"""
    if not item.counter:
        return rx.fragment()

    count = AppState.nav_counts[item.counter]
    # 「需要處理」與「告警」屬於待處理事項，用紅色凸顯。
    is_urgent = item.counter in ("action", "alert")
    return rx.cond(
        count > 0,
        rx.center(
            rx.text(count, size="1", weight="bold", line_height="1"),
            color=C.DANGER if is_urgent else C.TEXT_SECONDARY,
            background=C.DANGER_SOFT if is_urgent else C.BG_SUBTLE,
            border_radius=S.RADIUS_PILL,
            min_width="20px",
            height="18px",
            padding="0 6px",
            flex_shrink="0",
        ),
        rx.fragment(),
    )


def _nav_link(item: NavItem) -> rx.Component:
    """單一導覽項目。"""
    active = AppState.nav_key == item.key

    return rx.link(
        rx.hstack(
            rx.icon(
                item.icon,
                size=16,
                color=rx.cond(active, C.PRIMARY, C.TEXT_MUTED),
                flex_shrink="0",
            ),
            rx.text(
                item.label,
                size="2",
                weight=rx.cond(active, "bold", "regular"),
                color=rx.cond(active, C.PRIMARY, C.TEXT_SECONDARY),
                white_space="nowrap",
                overflow="hidden",
                text_overflow="ellipsis",
            ),
            rx.spacer(),
            _counter(item),
            spacing="2",
            align="center",
            width="100%",
        ),
        href=item.route,
        width="100%",
        padding="7px 10px",
        border_radius=S.RADIUS_SM,
        background=rx.cond(active, C.PRIMARY_SOFT, "transparent"),
        border_left="3px solid",
        border_color=rx.cond(active, C.PRIMARY, "transparent"),
        text_decoration="none",
        cursor="pointer",
        _hover={"background": rx.cond(active, C.PRIMARY_SOFT, C.BG_SUBTLE)},
    )


def _group(label: str, items: list[NavItem]) -> rx.Component:
    return rx.vstack(
        rx.text(
            label,
            size="1",
            weight="bold",
            color=C.TEXT_MUTED,
            letter_spacing="0.6px",
            padding="0 10px",
            margin_bottom="2px",
        ),
        *[_nav_link(item) for item in items],
        spacing="1",
        width="100%",
        align="start",
    )


def _footer() -> rx.Component:
    return rx.vstack(
        rx.box(height="1px", background=C.BORDER, width="100%", margin="8px 0"),
        _nav_link(SETTINGS_ITEM),
        rx.hstack(
            rx.icon("log-out", size=16, color=C.TEXT_MUTED, flex_shrink="0"),
            rx.text("登出", size="2", color=C.TEXT_SECONDARY),
            spacing="2",
            align="center",
            width="100%",
            padding="7px 10px",
            border_left="3px solid transparent",
            border_radius=S.RADIUS_SM,
            cursor="pointer",
            _hover={"background": C.BG_SUBTLE},
        ),
        spacing="1",
        width="100%",
        align="start",
    )


def sidebar() -> rx.Component:
    """固定在左側的導覽列。"""
    return rx.vstack(
        rx.vstack(
            *[_group(g.label, g.items) for g in NAV_GROUPS],
            spacing="4",
            width="100%",
            align="start",
        ),
        rx.spacer(),
        _footer(),
        spacing="2",
        width=S.SIDEBAR_W,
        height=f"calc(100vh - {S.HEADER_H})",
        padding="14px 10px 14px 8px",
        background=C.SIDEBAR_BG,
        border_right=f"1px solid {C.BORDER}",
        position="fixed",
        top=S.HEADER_H,
        left="0",
        overflow_y="auto",
        z_index="20",
        align="start",
    )
