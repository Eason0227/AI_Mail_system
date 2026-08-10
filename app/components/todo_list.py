"""待辦清單。

AI Analysis Panel 的「待辦事項」Tab 與待辦事項頁共用。

勾選狀態第一階段只存在前端 State（AppState.done_todo_ids），
不寫回資料來源；第二階段若要持久化，只需要在 Repository 增加寫入方法。
"""

from __future__ import annotations

import reflex as rx

from ..models import TodoItem
from ..states import AppState
from ..theme import C, S


def todo_row(todo: TodoItem, show_source: bool = False) -> rx.Component:
    """單一待辦項目。

    Args:
        show_source: 是否顯示來源郵件（待辦事項頁需要，AI Panel 內不需要）。
    """
    return rx.hstack(
        rx.checkbox(
            checked=todo.done,
            on_change=AppState.toggle_todo(todo.todo_id),
            size="2",
            color_scheme="green",
            margin_top="2px",
        ),
        rx.vstack(
            rx.text(
                todo.text,
                size="2",
                color=rx.cond(todo.done, C.TEXT_MUTED, C.TEXT),
                line_height="1.6",
                text_decoration=rx.cond(todo.done, "line-through", "none"),
            ),
            rx.hstack(
                rx.cond(
                    todo.deadline_label != "",
                    rx.hstack(
                        rx.icon("calendar-clock", size=11, color=C.TEXT_MUTED),
                        rx.text(
                            todo.deadline_label + " 前",
                            size="1",
                            color=C.TEXT_MUTED,
                        ),
                        spacing="1",
                        align="center",
                    ),
                    rx.fragment(),
                ),
                # show_source 是編譯期的 Python 值，直接分支即可，不需要 rx.cond。
                rx.cond(
                    todo.mail_subject != "",
                    rx.hstack(
                        rx.icon("mail", size=11, color=C.TEXT_MUTED),
                        rx.text(
                            todo.mail_subject,
                            size="1",
                            color=C.PRIMARY,
                            cursor="pointer",
                            overflow="hidden",
                            text_overflow="ellipsis",
                            white_space="nowrap",
                            on_click=AppState.open_mail_summary(todo.mail_id),
                        ),
                        spacing="1",
                        align="center",
                        min_width="0",
                    ),
                    rx.fragment(),
                )
                if show_source
                else rx.fragment(),
                spacing="3",
                align="center",
                width="100%",
                min_width="0",
            ),
            spacing="1",
            align="start",
            flex="1",
            min_width="0",
        ),
        spacing="3",
        align="start",
        width="100%",
        padding="9px 10px",
        background=rx.cond(todo.done, C.SUCCESS_SOFT, C.SURFACE),
        border="1px solid",
        border_color=rx.cond(todo.done, C.SUCCESS_BORDER, C.BORDER),
        border_radius=S.RADIUS_SM,
    )


def todo_checklist(
    items: rx.Var, show_source: bool = False, spacing: str = "2"
) -> rx.Component:
    """待辦清單容器。"""
    return rx.vstack(
        rx.foreach(items, lambda t: todo_row(t, show_source=show_source)),
        spacing=spacing,
        width="100%",
        align="start",
    )
