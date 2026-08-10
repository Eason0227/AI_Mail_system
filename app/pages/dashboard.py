"""今日總覽。"""

from __future__ import annotations

import reflex as rx

from ..components import (
    action_card,
    alert_card,
    daily_brief,
    empty_state,
    kpi_row,
    page_layout,
    page_title_bar,
    section_header,
)
from ..states import AppState
from ..theme import C


def _action_section() -> rx.Component:
    """需要您處理。"""
    return rx.vstack(
        section_header(
            "需要您處理",
            icon="circle-alert",
            action=rx.link(
                rx.hstack(
                    rx.text("查看全部", size="1", color=C.PRIMARY),
                    rx.icon("chevron-right", size=13, color=C.PRIMARY),
                    spacing="0",
                    align="center",
                ),
                href="/mail/action",
                text_decoration="none",
            ),
        ),
        rx.cond(
            AppState.action_mails.length() > 0,
            rx.vstack(
                rx.foreach(AppState.action_mails, action_card),
                spacing="3",
                width="100%",
            ),
            empty_state("目前沒有需要您處理的郵件", icon="check-check", height="180px"),
        ),
        spacing="0",
        width="100%",
        align="start",
    )


def _alert_section() -> rx.Component:
    """系統 / 設備事件。"""
    return rx.vstack(
        section_header(
            "系統 / 設備事件",
            icon="triangle-alert",
            action=rx.link(
                rx.hstack(
                    rx.text("查看全部", size="1", color=C.PRIMARY),
                    rx.icon("chevron-right", size=13, color=C.PRIMARY),
                    spacing="0",
                    align="center",
                ),
                href="/alerts",
                text_decoration="none",
            ),
        ),
        rx.cond(
            AppState.alerts.length() > 0,
            rx.vstack(
                rx.foreach(AppState.alerts, alert_card),
                spacing="3",
                width="100%",
            ),
            empty_state("目前沒有進行中的事件", icon="shield-check", height="180px"),
        ),
        spacing="0",
        width="100%",
        align="start",
    )


def dashboard_page() -> rx.Component:
    """首頁：KPI → AI 今日重點 → 需要您處理 / 系統事件。"""
    return page_layout(
        page_title_bar(),
        kpi_row(),
        daily_brief(),
        rx.grid(
            _action_section(),
            _alert_section(),
            columns="2",
            spacing="4",
            width="100%",
            align_items="start",
            style={"grid_template_columns": "1.35fr 1fr"},
        ),
    )
