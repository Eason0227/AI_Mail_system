"""首頁 KPI 卡片。

數字一律來自 State（由 DashboardService 計算），這裡不做任何加總。
"""

from __future__ import annotations

from typing import Any

import reflex as rx

from ..states import AppState
from ..theme import C, S


def kpi_card(
    label: str,
    value: Any,
    icon: str,
    accent: str,
    accent_soft: str,
    hint: Any = "",
    href: str = "",
) -> rx.Component:
    """單張 KPI 卡。"""
    body = rx.hstack(
        rx.vstack(
            rx.text(label, size="2", color=C.TEXT_SECONDARY, weight="medium"),
            rx.text(
                value,
                size="7",
                weight="bold",
                color=C.TEXT,
                line_height="1.1",
            ),
            rx.cond(
                hint != "",
                rx.text(hint, size="1", color=C.TEXT_MUTED),
                rx.box(height="14px"),
            ),
            spacing="1",
            align="start",
        ),
        rx.spacer(),
        rx.center(
            rx.icon(icon, size=20, color=accent),
            background=accent_soft,
            border_radius=S.RADIUS_SM,
            width="38px",
            height="38px",
            flex_shrink="0",
        ),
        width="100%",
        align="start",
    )

    card = rx.box(
        body,
        background=C.SURFACE,
        border=f"1px solid {C.BORDER}",
        border_top=f"3px solid {accent}",
        border_radius=S.RADIUS,
        box_shadow=S.SHADOW,
        padding="14px 16px",
        width="100%",
        height="100%",
        transition="box-shadow .15s ease",
        _hover={"box_shadow": S.SHADOW_HOVER},
    )

    if not href:
        return card
    return rx.link(card, href=href, text_decoration="none", width="100%")


def kpi_row() -> rx.Component:
    """五張 KPI 卡（今日郵件 / 重要郵件 / 待辦 / 系統事件 / 一般資訊）。"""
    return rx.grid(
        kpi_card(
            "今日郵件",
            AppState.kpi.total_today,
            "mail",
            C.PRIMARY,
            C.PRIMARY_SOFT,
            hint=rx.cond(
                AppState.kpi.unread_today > 0,
                f"{AppState.kpi.unread_today} 封未讀",
                "全部已讀",
            ),
            href="/mail/history",
        ),
        kpi_card(
            "重要郵件",
            AppState.kpi.important,
            "star",
            C.STAR,
            C.WARNING_SOFT,
            hint="重要度 4 星以上",
            href="/mail/important",
        ),
        kpi_card(
            "待辦事項",
            AppState.kpi_todo_display,
            "list-checks",
            C.SUCCESS,
            C.SUCCESS_SOFT,
            hint=rx.cond(
                AppState.kpi.overdue > 0,
                f"{AppState.kpi.overdue} 項已逾期",
                f"{AppState.kpi.due_soon} 項即將到期",
            ),
            href="/todo",
        ),
        kpi_card(
            "系統 / 設備事件",
            AppState.kpi.system_events,
            "triangle-alert",
            C.DANGER,
            C.DANGER_SOFT,
            hint=f"{AppState.kpi.resolved_alerts} 件已解決",
            href="/alerts",
        ),
        kpi_card(
            "一般資訊",
            AppState.kpi.general_info,
            "info",
            C.INFO,
            C.INFO_SOFT,
            hint="不需立即處理",
            href="/mail/info",
        ),
        columns="5",
        spacing="3",
        width="100%",
    )
