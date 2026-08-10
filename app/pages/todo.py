"""待辦事項頁。

顯示 AI 從所有郵件拆解出的行動項目。
勾選狀態第一階段只存在前端 State，不寫回資料來源。
"""

from __future__ import annotations

import reflex as rx

from ..components import (
    ai_tag,
    card,
    empty_state,
    page_layout,
    page_title_bar,
    todo_checklist,
)
from ..states import AppState
from ..theme import C, S


def _progress() -> rx.Component:
    """完成度。"""
    return rx.hstack(
        rx.vstack(
            rx.text("未完成", size="1", color=C.TEXT_MUTED),
            rx.text(
                AppState.todo_open_count,
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
            rx.text("已完成", size="1", color=C.TEXT_MUTED),
            rx.text(
                AppState.todo_done_count,
                size="6",
                weight="bold",
                color=C.SUCCESS,
                line_height="1.1",
            ),
            spacing="0",
            align="start",
        ),
        rx.box(width="1px", height="40px", background=C.BORDER),
        rx.vstack(
            rx.text("逾期事項", size="1", color=C.TEXT_MUTED),
            rx.text(
                AppState.kpi.overdue,
                size="6",
                weight="bold",
                color=C.WARNING,
                line_height="1.1",
            ),
            spacing="0",
            align="start",
        ),
        rx.spacer(),
        rx.vstack(
            ai_tag("AI 自郵件拆解"),
            rx.text(
                "勾選僅暫存於畫面，不會寫回郵件系統",
                size="1",
                color=C.TEXT_MUTED,
            ),
            spacing="2",
            align="end",
        ),
        spacing="5",
        align="center",
        width="100%",
    )


def todo_page() -> rx.Component:
    return page_layout(
        page_title_bar(),
        card(_progress()),
        rx.cond(
            AppState.visible_todos.length() > 0,
            rx.box(
                todo_checklist(AppState.visible_todos, show_source=True),
                width="100%",
            ),
            empty_state(
                "目前沒有待辦事項",
                "AI 會在分析郵件時自動拆解行動項目",
                icon="list-checks",
            ),
        ),
    )
