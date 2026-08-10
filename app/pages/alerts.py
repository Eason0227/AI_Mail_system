"""系統 / 設備事件頁。"""

from __future__ import annotations

import reflex as rx

from ..components import (
    alert_card,
    card,
    empty_state,
    page_layout,
    page_title_bar,
)
from ..states import AppState
from ..theme import C


def _summary() -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.text("進行中", size="1", color=C.TEXT_MUTED),
            rx.text(
                AppState.kpi.system_events,
                size="6",
                weight="bold",
                color=C.DANGER,
                line_height="1.1",
            ),
            spacing="0",
            align="start",
        ),
        rx.box(width="1px", height="40px", background=C.BORDER),
        rx.vstack(
            rx.text("已解決", size="1", color=C.TEXT_MUTED),
            rx.text(
                AppState.kpi.resolved_alerts,
                size="6",
                weight="bold",
                color=C.SUCCESS,
                line_height="1.1",
            ),
            spacing="0",
            align="start",
        ),
        rx.spacer(),
        rx.hstack(
            rx.icon("info", size=13, color=C.TEXT_MUTED),
            rx.text(
                "事件資料與郵件同源，點「查看事件」可跳到對應的通知信。",
                size="1",
                color=C.TEXT_MUTED,
            ),
            spacing="2",
            align="center",
        ),
        spacing="5",
        align="center",
        width="100%",
    )


def alerts_page() -> rx.Component:
    return page_layout(
        page_title_bar(),
        card(_summary()),
        rx.cond(
            AppState.alerts.length() > 0,
            rx.grid(
                rx.foreach(AppState.alerts, alert_card),
                columns="2",
                spacing="3",
                width="100%",
                align_items="start",
            ),
            empty_state(
                "目前沒有系統 / 設備事件",
                icon="shield-check",
            ),
        ),
    )
