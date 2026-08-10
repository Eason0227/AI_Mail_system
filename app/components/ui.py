"""共用視覺元件。

這裡只放「跟業務無關」的外觀零件：卡片、區塊標題、標籤、空狀態…

顏色對應為什麼要用 rx.match
---------------------------
在 rx.foreach 內拿到的是 Var 而不是 Python 字串，
不能寫 ``theme.category_color(mail.ai.category)`` 這種即時查表。
因此把 theme.py 的對照表在編譯期展開成 rx.match，
顏色定義仍然只有 theme.py 一份。
"""

from __future__ import annotations

from typing import Any, Optional

import reflex as rx

from ..theme import CATEGORY_COLORS, SEVERITY_COLORS, C, S


# --------------------------------------------------------------------------
# Var 安全的顏色對應
# --------------------------------------------------------------------------
def _match_color(value: Any, table: dict, index: int, default: str) -> Any:
    """把 (文字色, 底色, 邊框色) 對照表展開成 rx.match。"""
    cases = [(key, colors[index]) for key, colors in table.items()]
    return rx.match(value, *cases, default)


def category_fg(category: Any) -> Any:
    return _match_color(category, CATEGORY_COLORS, 0, C.INFO)


def category_bg(category: Any) -> Any:
    return _match_color(category, CATEGORY_COLORS, 1, C.INFO_SOFT)


def category_border(category: Any) -> Any:
    return _match_color(category, CATEGORY_COLORS, 2, C.INFO_BORDER)


def severity_fg(severity: Any) -> Any:
    return _match_color(severity, SEVERITY_COLORS, 0, C.INFO)


def severity_bg(severity: Any) -> Any:
    return _match_color(severity, SEVERITY_COLORS, 1, C.INFO_SOFT)


def severity_border(severity: Any) -> Any:
    return _match_color(severity, SEVERITY_COLORS, 2, C.INFO_BORDER)


# --------------------------------------------------------------------------
# 容器
# --------------------------------------------------------------------------
def card(*children, **props) -> rx.Component:
    """白底卡片。"""
    style = {
        "background": C.SURFACE,
        "border": f"1px solid {C.BORDER}",
        "border_radius": S.RADIUS,
        "box_shadow": S.SHADOW,
        "padding": "16px",
        "width": "100%",
    }
    style.update(props.pop("style", {}))
    return rx.box(*children, style=style, **props)


def panel(*children, **props) -> rx.Component:
    """無內距的面板（給需要自行控制捲動的三欄工作區使用）。"""
    style = {
        "background": C.SURFACE,
        "border": f"1px solid {C.BORDER}",
        "border_radius": S.RADIUS,
        "box_shadow": S.SHADOW,
        "overflow": "hidden",
        "display": "flex",
        "flex_direction": "column",
        "min_height": "0",
    }
    style.update(props.pop("style", {}))
    return rx.box(*children, style=style, **props)


def section_header(
    title: str,
    subtitle: str = "",
    icon: str = "",
    action: Optional[rx.Component] = None,
) -> rx.Component:
    """區塊標題列。"""
    # title / subtitle / icon 都是編譯期的 Python 值，直接分支即可。
    left = rx.hstack(
        rx.icon(icon, size=16, color=C.TEXT_SECONDARY) if icon else rx.fragment(),
        rx.text(title, size="3", weight="bold", color=C.TEXT),
        rx.text(subtitle, size="2", color=C.TEXT_MUTED) if subtitle else rx.fragment(),
        spacing="2",
        align="center",
    )
    return rx.hstack(
        left,
        rx.spacer(),
        action if action is not None else rx.fragment(),
        width="100%",
        align="center",
        margin_bottom="10px",
    )


# --------------------------------------------------------------------------
# 標籤
# --------------------------------------------------------------------------
def pill(
    text: Any,
    fg: Any = C.TEXT_SECONDARY,
    bg: Any = C.INFO_SOFT,
    border: Any = C.INFO_BORDER,
    icon: str = "",
    **props,
) -> rx.Component:
    """圓角小標籤。

    icon 必須是編譯期常數（lucide 圖示名稱），不可傳 Var。
    """
    return rx.hstack(
        rx.icon(icon, size=12) if icon else rx.fragment(),
        rx.text(text, size="1", weight="medium", line_height="1"),
        spacing="1",
        align="center",
        color=fg,
        background=bg,
        border=f"1px solid",
        border_color=border,
        border_radius=S.RADIUS_PILL,
        padding="3px 9px",
        flex_shrink="0",
        **props,
    )


def category_badge(category: Any, label: Any) -> rx.Component:
    """郵件分類標籤（顏色隨分類變化）。"""
    return pill(
        label,
        fg=category_fg(category),
        bg=category_bg(category),
        border=category_border(category),
    )


def severity_badge(severity: Any, label: Any) -> rx.Component:
    """事件嚴重度標籤。"""
    return pill(
        label,
        fg=severity_fg(severity),
        bg=severity_bg(severity),
        border=severity_border(severity),
    )


def deadline_badge(analysis: Any) -> rx.Component:
    """期限標籤：逾期紅色、三天內橘色、其餘灰色。"""
    return rx.cond(
        analysis.has_deadline,
        pill(
            rx.cond(
                analysis.is_overdue,
                "已逾期 " + analysis.deadline_label,
                analysis.deadline_label,
            ),
            fg=rx.cond(
                analysis.is_overdue,
                C.DANGER,
                rx.cond(analysis.is_due_soon, C.WARNING, C.TEXT_SECONDARY),
            ),
            bg=rx.cond(
                analysis.is_overdue,
                C.DANGER_SOFT,
                rx.cond(analysis.is_due_soon, C.WARNING_SOFT, C.INFO_SOFT),
            ),
            border=rx.cond(
                analysis.is_overdue,
                C.DANGER_BORDER,
                rx.cond(analysis.is_due_soon, C.WARNING_BORDER, C.INFO_BORDER),
            ),
            icon="calendar-clock",
        ),
        rx.fragment(),
    )


def ai_tag(text: str = "AI 生成") -> rx.Component:
    """明確標示「這段內容是 AI 產生的」。

    需求要求 AI 內容不可與原始郵件混淆，凡是 AI 產出的區塊都要帶這個標記。
    """
    return pill(
        text,
        fg=C.PURPLE,
        bg=C.PURPLE_SOFT,
        border=C.PURPLE_BORDER,
        icon="sparkles",
    )


def stars(value: Any) -> rx.Component:
    """重要度星號。"""
    return rx.text(value, size="3", color=C.STAR, letter_spacing="2px")


# --------------------------------------------------------------------------
# 狀態
# --------------------------------------------------------------------------
def empty_state(
    title: str, hint: str = "", icon: str = "inbox", height: str = "220px"
) -> rx.Component:
    """空清單提示。"""
    return rx.center(
        rx.vstack(
            rx.icon(icon, size=28, color=C.TEXT_MUTED),
            rx.text(title, size="2", color=C.TEXT_SECONDARY, weight="medium"),
            rx.text(hint, size="1", color=C.TEXT_MUTED) if hint else rx.fragment(),
            spacing="2",
            align="center",
        ),
        width="100%",
        height=height,
    )


def field_row(label: str, value: Any, value_color: str = C.TEXT) -> rx.Component:
    """「欄位：值」的一列。"""
    return rx.hstack(
        rx.text(
            label,
            size="1",
            color=C.TEXT_MUTED,
            width="72px",
            flex_shrink="0",
        ),
        rx.text(value, size="2", color=value_color, weight="medium"),
        spacing="2",
        align="start",
        width="100%",
    )


def toolbar_button(
    label: str,
    icon: str = "",
    on_click: Any = None,
    variant: str = "soft",
    **props,
) -> rx.Component:
    """統一樣式的小按鈕。

    variant: primary / soft / ghost

    icon 必須是編譯期常數。需要依狀態換圖示時，請對整顆按鈕做 rx.cond。
    """
    palettes = {
        "primary": (C.TEXT_INVERSE, C.PRIMARY, C.PRIMARY),
        "soft": (C.TEXT_SECONDARY, C.SURFACE, C.BORDER_STRONG),
        "ghost": (C.TEXT_SECONDARY, "transparent", "transparent"),
    }
    fg, bg, border = palettes.get(variant, palettes["soft"])
    hover_bg = C.PRIMARY_HOVER if variant == "primary" else C.BG_SUBTLE

    return rx.button(
        rx.icon(icon, size=14) if icon else rx.fragment(),
        rx.text(label, size="1", weight="medium"),
        on_click=on_click,
        color=fg,
        background=bg,
        border=f"1px solid {border}",
        border_radius=S.RADIUS_SM,
        padding="0 10px",
        height="30px",
        cursor="pointer",
        _hover={"background": hover_bg},
        **props,
    )
