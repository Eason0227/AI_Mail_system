"""系統 / 設備事件卡片。"""

from __future__ import annotations

import reflex as rx

from ..models import SystemAlert
from ..states import AppState
from ..theme import C, S
from .ui import severity_badge, severity_border, severity_fg, toolbar_button


def _metric(label: str, value: rx.Var, emphasis: rx.Var | bool = False) -> rx.Component:
    """事件的單一數值欄位。"""
    return rx.vstack(
        rx.text(label, size="1", color=C.TEXT_MUTED, line_height="1.2"),
        rx.text(
            value,
            size="4",
            weight="bold",
            color=rx.cond(emphasis, C.DANGER, C.TEXT),
            line_height="1.3",
        ),
        spacing="0",
        align="start",
    )


def alert_card(alert: SystemAlert) -> rx.Component:
    """單張事件卡。"""
    is_active = (alert.status == "open") | (alert.status == "monitoring")

    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.icon(
                    "cpu",
                    size=16,
                    color=severity_fg(alert.severity),
                    flex_shrink="0",
                ),
                rx.text(
                    alert.equipment,
                    size="3",
                    weight="bold",
                    color=C.TEXT,
                    font_family="ui-monospace, SFMono-Regular, monospace",
                ),
                severity_badge(alert.severity, alert.severity_label),
                # 同類告警被聚合時顯示次數（公司資料的 alert_key 聚合結果）。
                rx.cond(
                    alert.occurrence_count > 1,
                    rx.text(
                        "×" + alert.occurrence_count.to_string(),
                        size="1",
                        weight="bold",
                        color=C.TEXT_SECONDARY,
                        background=C.BG_SUBTLE,
                        border_radius=S.RADIUS_PILL,
                        padding="2px 8px",
                    ),
                    rx.fragment(),
                ),
                rx.spacer(),
                rx.text(alert.status_label, size="1", color=C.TEXT_MUTED),
                spacing="2",
                align="center",
                width="100%",
            ),
            rx.text(alert.alert_type, size="2", weight="medium", color=C.TEXT),
            rx.text(
                alert.description,
                size="1",
                color=C.TEXT_SECONDARY,
                line_height="1.6",
            ),
            rx.hstack(
                _metric(alert.metric_label, alert.metric_value, emphasis=is_active),
                rx.box(width="1px", height="34px", background=C.BORDER),
                _metric("Duration", alert.duration_label),
                rx.box(width="1px", height="34px", background=C.BORDER),
                _metric("負責單位", alert.owner),
                spacing="4",
                align="center",
                width="100%",
                padding="10px 12px",
                background=C.SURFACE_ALT,
                border=f"1px solid {C.BORDER}",
                border_radius=S.RADIUS_SM,
            ),
            rx.hstack(
                rx.text(
                    alert.occurred_at_label + " 發生",
                    size="1",
                    color=C.TEXT_MUTED,
                ),
                rx.spacer(),
                rx.cond(
                    alert.related_mail_id != "",
                    toolbar_button(
                        "查看事件",
                        icon="arrow-right",
                        variant="primary",
                        on_click=AppState.open_mail_summary(alert.related_mail_id),
                    ),
                    rx.fragment(),
                ),
                width="100%",
                align="center",
            ),
            spacing="2",
            width="100%",
            align="start",
        ),
        width="100%",
        padding="14px",
        background=C.SURFACE,
        border="1px solid",
        border_color=severity_border(alert.severity),
        border_left="3px solid",
        border_left_color=severity_fg(alert.severity),
        border_radius=S.RADIUS,
        box_shadow=S.SHADOW,
        opacity=rx.cond(is_active, "1", "0.72"),
        transition="box-shadow .15s ease",
        _hover={"box_shadow": S.SHADOW_HOVER},
    )
