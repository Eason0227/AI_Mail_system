"""AI Analysis Panel（三欄工作區右欄，30%）。

**這一欄的所有內容都是 AI 產生的**，因此整體以紫色系與原始郵件區隔，
每個區塊都帶「AI」標記，避免與 Original Mail 混淆。

Tabs：摘要 / 待辦事項 / 建議處置 / 建議回覆
"""

from __future__ import annotations

import reflex as rx

from ..models import KeyFact
from ..states import TAB_RECOMMEND, TAB_REPLY, TAB_SUMMARY, TAB_TODO, AppState
from ..theme import C, S
from .todo_list import todo_checklist
from .ui import ai_tag, category_badge, empty_state, panel, pill, toolbar_button


# --------------------------------------------------------------------------
# Tab 列
# --------------------------------------------------------------------------
_TABS = (
    (TAB_SUMMARY, "摘要", "scan-text"),
    (TAB_TODO, "待辦事項", "list-checks"),
    (TAB_RECOMMEND, "建議處置", "lightbulb"),
    (TAB_REPLY, "建議回覆", "reply"),
)


def _tab_bar() -> rx.Component:
    def tab(key: str, label: str, icon: str) -> rx.Component:
        active = AppState.ai_tab == key
        return rx.hstack(
            rx.icon(
                icon,
                size=13,
                color=rx.cond(active, C.PURPLE, C.TEXT_MUTED),
                flex_shrink="0",
            ),
            rx.text(
                label,
                size="1",
                weight=rx.cond(active, "bold", "regular"),
                color=rx.cond(active, C.PURPLE, C.TEXT_SECONDARY),
                white_space="nowrap",
            ),
            spacing="1",
            align="center",
            justify="center",
            on_click=AppState.set_ai_tab(key),
            flex="1",
            padding="9px 4px",
            cursor="pointer",
            border_bottom="2px solid",
            border_color=rx.cond(active, C.PURPLE, "transparent"),
            background=rx.cond(active, C.PURPLE_SOFT, "transparent"),
            _hover={"background": rx.cond(active, C.PURPLE_SOFT, C.BG_SUBTLE)},
        )

    return rx.hstack(
        *[tab(key, label, icon) for key, label, icon in _TABS],
        spacing="0",
        width="100%",
        border_bottom=f"1px solid {C.BORDER}",
        flex_shrink="0",
    )


# --------------------------------------------------------------------------
# 摘要
# --------------------------------------------------------------------------
def _key_fact(fact: KeyFact) -> rx.Component:
    return rx.hstack(
        rx.text(
            fact.label,
            size="1",
            color=C.TEXT_MUTED,
            width="88px",
            flex_shrink="0",
        ),
        rx.text(
            fact.value,
            size="2",
            weight=rx.cond(fact.emphasis, "bold", "medium"),
            color=rx.cond(fact.emphasis, C.DANGER, C.TEXT),
        ),
        spacing="2",
        align="start",
        width="100%",
        padding="6px 0",
        border_bottom=f"1px dashed {C.BORDER}",
    )


def _key_info_shell(*children) -> rx.Component:
    """關鍵資訊卡片外框。"""
    return rx.vstack(
        rx.hstack(
            rx.icon("key-round", size=13, color=C.TEXT_SECONDARY),
            rx.text("關鍵資訊", size="1", weight="bold", color=C.TEXT_SECONDARY),
            ai_tag("AI 擷取"),
            spacing="2",
            align="center",
        ),
        *children,
        spacing="2",
        align="start",
        width="100%",
        padding="12px",
        background=C.SURFACE,
        border=f"1px solid {C.BORDER}",
        border_radius=S.RADIUS_SM,
    )


def _key_fact_card(ai) -> rx.Component:
    """label / value 配對版（Mock 資料）。"""
    return _key_info_shell(
        rx.vstack(rx.foreach(ai.key_facts, _key_fact), spacing="0", width="100%")
    )


def _key_point_card(ai) -> rx.Component:
    """純文字條列版（公司 pipeline 的 key_points）。"""
    return _key_info_shell(
        rx.vstack(
            rx.foreach(
                ai.key_points,
                lambda point: rx.hstack(
                    rx.box(
                        width="5px",
                        height="5px",
                        border_radius=S.RADIUS_PILL,
                        background=C.TEXT_MUTED,
                        margin_top="8px",
                        flex_shrink="0",
                    ),
                    rx.text(point, size="2", color=C.TEXT, line_height="1.7"),
                    spacing="2",
                    align="start",
                    width="100%",
                ),
            ),
            spacing="1",
            width="100%",
        )
    )


def _summary_tab() -> rx.Component:
    ai = AppState.selected_mail.ai
    sender = AppState.selected_mail.sender

    return rx.vstack(
        # AI 重點摘要
        rx.vstack(
            rx.hstack(
                ai_tag("AI 重點摘要"),
                rx.spacer(),
                rx.text(ai.model_name, size="1", color=C.TEXT_MUTED),
                width="100%",
                align="center",
            ),
            rx.text(
                ai.summary,
                size="2",
                color=C.TEXT,
                line_height="1.8",
            ),
            spacing="2",
            align="start",
            width="100%",
            padding="12px",
            background=C.PURPLE_SOFT,
            border=f"1px solid {C.PURPLE_BORDER}",
            border_radius=S.RADIUS_SM,
        ),
        # 判定結果
        rx.vstack(
            rx.hstack(
                rx.text("重要度", size="1", color=C.TEXT_MUTED, width="88px"),
                rx.text(
                    ai.importance_stars,
                    size="3",
                    color=C.STAR,
                    letter_spacing="2px",
                    line_height="1",
                ),
                rx.text(f"{ai.importance} / 5", size="1", color=C.TEXT_MUTED),
                spacing="2",
                align="center",
                width="100%",
            ),
            rx.hstack(
                rx.text("郵件分類", size="1", color=C.TEXT_MUTED, width="88px"),
                category_badge(ai.category, ai.category_label),
                rx.cond(
                    ai.action_required,
                    rx.text("需要您處理", size="1", color=C.DANGER, weight="medium"),
                    rx.fragment(),
                ),
                spacing="2",
                align="center",
                width="100%",
            ),
            rx.hstack(
                rx.text("Deadline", size="1", color=C.TEXT_MUTED, width="88px"),
                rx.cond(
                    ai.has_deadline,
                    rx.hstack(
                        rx.text(
                            ai.deadline_label,
                            size="2",
                            weight="bold",
                            color=rx.cond(
                                ai.is_overdue,
                                C.DANGER,
                                rx.cond(ai.is_due_soon, C.WARNING, C.TEXT),
                            ),
                        ),
                        rx.text(
                            rx.cond(
                                ai.is_overdue,
                                "已逾期",
                                "剩 " + ai.deadline_days_left.to_string() + " 天",
                            ),
                            size="1",
                            color=rx.cond(ai.is_overdue, C.DANGER, C.TEXT_MUTED),
                        ),
                        spacing="2",
                        align="center",
                    ),
                    rx.text("無", size="2", color=C.TEXT_MUTED),
                ),
                spacing="2",
                align="center",
                width="100%",
            ),
            rx.hstack(
                rx.text("寄件人", size="1", color=C.TEXT_MUTED, width="88px"),
                rx.text(sender.name, size="2", weight="medium", color=C.TEXT),
                rx.cond(
                    sender.is_key_person,
                    rx.hstack(
                        rx.icon("badge-check", size=12, color=C.PRIMARY),
                        rx.text("關鍵窗口", size="1", color=C.PRIMARY),
                        spacing="1",
                        align="center",
                    ),
                    rx.fragment(),
                ),
                spacing="2",
                align="center",
                width="100%",
            ),
            # 收件人關係：公司端 LLM 判定本人是直接收件人 / 僅副本 / 群發。
            # Mock 沒有這個欄位，空字串時整列不顯示。
            rx.cond(
                ai.addressed_to_label != "",
                rx.hstack(
                    rx.text("收件關係", size="1", color=C.TEXT_MUTED, width="88px"),
                    pill(
                        ai.addressed_to_label,
                        fg=rx.cond(ai.addressed_to == "direct", C.PRIMARY, C.TEXT_SECONDARY),
                        bg=rx.cond(ai.addressed_to == "direct", C.PRIMARY_SOFT, C.INFO_SOFT),
                        border=rx.cond(
                            ai.addressed_to == "direct", C.PRIMARY_BORDER, C.INFO_BORDER
                        ),
                    ),
                    spacing="2",
                    align="center",
                    width="100%",
                ),
                rx.fragment(),
            ),
            spacing="2",
            width="100%",
            align="start",
            padding="12px",
            background=C.SURFACE,
            border=f"1px solid {C.BORDER}",
            border_radius=S.RADIUS_SM,
        ),
        # 關鍵資訊。
        # Mock 提供 key_facts（label/value 配對），公司 pipeline 只有
        # key_points（純文字條列），因此兩種都支援：有配對就用表格，否則條列。
        rx.cond(
            ai.key_facts.length() > 0,
            _key_fact_card(ai),
            rx.cond(ai.key_points.length() > 0, _key_point_card(ai), rx.fragment()),
        ),
        spacing="3",
        width="100%",
        align="start",
    )


# --------------------------------------------------------------------------
# 待辦事項
# --------------------------------------------------------------------------
def _todo_tab() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            ai_tag("AI 拆解的待辦"),
            rx.spacer(),
            rx.text(
                "勾選僅暫存於畫面",
                size="1",
                color=C.TEXT_MUTED,
            ),
            width="100%",
            align="center",
        ),
        rx.cond(
            AppState.selected_mail.ai.todos.length() > 0,
            todo_checklist(AppState.selected_todos),
            empty_state("這封郵件沒有待辦事項", icon="list-checks", height="160px"),
        ),
        spacing="3",
        width="100%",
        align="start",
    )


# --------------------------------------------------------------------------
# 建議處置
# --------------------------------------------------------------------------
def _recommend_tab() -> rx.Component:
    ai = AppState.selected_mail.ai

    return rx.vstack(
        rx.hstack(
            ai_tag("AI 建議"),
            rx.text(
                "以下為 AI 建議，非郵件原文",
                size="1",
                color=C.TEXT_MUTED,
            ),
            spacing="2",
            align="center",
            width="100%",
        ),
        rx.cond(
            ai.recommendations.length() > 0,
            rx.vstack(
                rx.foreach(
                    ai.recommendations,
                    lambda item, index: rx.hstack(
                        rx.center(
                            rx.text(
                                index + 1,
                                size="1",
                                weight="bold",
                                color=C.PURPLE,
                                line_height="1",
                            ),
                            background=C.PURPLE_SOFT,
                            border=f"1px solid {C.PURPLE_BORDER}",
                            border_radius=S.RADIUS_PILL,
                            width="20px",
                            height="20px",
                            flex_shrink="0",
                            margin_top="2px",
                        ),
                        rx.text(
                            item,
                            size="2",
                            color=C.TEXT,
                            line_height="1.7",
                            flex="1",
                        ),
                        spacing="3",
                        align="start",
                        width="100%",
                        padding="9px 10px",
                        background=C.SURFACE,
                        border=f"1px solid {C.BORDER}",
                        border_left=f"3px solid {C.PURPLE}",
                        border_radius=S.RADIUS_SM,
                    ),
                ),
                spacing="2",
                width="100%",
            ),
            empty_state("這封郵件沒有 AI 建議", icon="lightbulb", height="160px"),
        ),
        spacing="3",
        width="100%",
        align="start",
    )


# --------------------------------------------------------------------------
# 建議回覆
# --------------------------------------------------------------------------
def _reply_tab() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            ai_tag("AI 回覆草稿"),
            rx.spacer(),
            rx.text("不會實際寄出", size="1", color=C.TEXT_MUTED),
            width="100%",
            align="center",
        ),
        rx.cond(
            AppState.reply_generated,
            # ---- 已產生 ----
            rx.vstack(
                rx.text_area(
                    value=AppState.reply_draft,
                    on_change=AppState.on_reply_change,
                    width="100%",
                    min_height="260px",
                    size="2",
                    background=C.SURFACE,
                    border=f"1px solid {C.PURPLE_BORDER}",
                    border_radius=S.RADIUS_SM,
                    line_height="1.75",
                ),
                rx.hstack(
                    toolbar_button(
                        "重新產生",
                        icon="refresh-cw",
                        on_click=AppState.regenerate_reply,
                    ),
                    toolbar_button(
                        "複製",
                        icon="copy",
                        on_click=AppState.copy_reply,
                    ),
                    rx.spacer(),
                    # icon 必須是編譯期常數，因此整顆按鈕做 rx.cond 分支。
                    rx.cond(
                        AppState.draft_saved,
                        toolbar_button(
                            "已建立草稿",
                            icon="check",
                            variant="primary",
                            on_click=AppState.save_draft,
                        ),
                        toolbar_button(
                            "建立 Draft",
                            icon="file-plus",
                            variant="primary",
                            on_click=AppState.save_draft,
                        ),
                    ),
                    spacing="2",
                    width="100%",
                    align="center",
                ),
                rx.hstack(
                    rx.icon("info", size=12, color=C.TEXT_MUTED),
                    rx.text(
                        "第一階段不實作寄信功能，草稿僅顯示於畫面。",
                        size="1",
                        color=C.TEXT_MUTED,
                    ),
                    spacing="1",
                    align="center",
                ),
                spacing="2",
                width="100%",
                align="start",
            ),
            # ---- 資料來源沒有草稿 / 尚未產生 ----
            rx.cond(
                AppState.reply_unavailable,
                rx.center(
                    rx.vstack(
                        rx.icon("file-x", size=26, color=C.TEXT_MUTED),
                        rx.text(
                            "目前的資料來源沒有回覆草稿",
                            size="2",
                            weight="medium",
                            color=C.TEXT_SECONDARY,
                        ),
                        rx.text(
                            "公司端 Step C 尚未輸出 reply_draft 欄位。"
                            "需在該階段的 prompt 補上，Dashboard 這側不需要修改。",
                            size="1",
                            color=C.TEXT_MUTED,
                            line_height="1.7",
                            text_align="center",
                            max_width="300px",
                        ),
                        spacing="2",
                        align="center",
                    ),
                    width="100%",
                    height="240px",
                ),
                rx.center(
                    rx.vstack(
                        rx.icon("sparkles", size=26, color=C.PURPLE),
                        rx.text(
                            "尚未產生回覆草稿",
                            size="2",
                            weight="medium",
                            color=C.TEXT_SECONDARY,
                        ),
                        rx.text(
                            "AI 會依這封郵件的內容與待辦產生草稿",
                            size="1",
                            color=C.TEXT_MUTED,
                        ),
                        rx.button(
                            rx.cond(
                                AppState.reply_generating,
                                rx.spinner(size="1"),
                                rx.icon("wand-sparkles", size=15),
                            ),
                            rx.text("產生回覆草稿", size="2", weight="medium"),
                            on_click=AppState.generate_reply,
                            disabled=AppState.reply_generating,
                            color=C.TEXT_INVERSE,
                            background=C.PURPLE,
                            border_radius=S.RADIUS_SM,
                            height="36px",
                            padding="0 16px",
                            cursor="pointer",
                            margin_top="6px",
                            _hover={"background": "#6B3ED8"},
                        ),
                        spacing="2",
                        align="center",
                    ),
                    width="100%",
                    height="240px",
                ),
            ),
        ),
        spacing="3",
        width="100%",
        align="start",
    )


# --------------------------------------------------------------------------
# 主體
# --------------------------------------------------------------------------
def _no_analysis() -> rx.Component:
    return empty_state(
        "這封郵件尚無 AI 分析結果",
        "第二階段接上公司端 LLM 後會自動補齊",
        icon="sparkles",
        height="100%",
    )


def ai_analysis_panel() -> rx.Component:
    """右欄：AI 分析。"""
    return panel(
        rx.hstack(
            rx.icon("sparkles", size=15, color=C.PURPLE),
            rx.text("AI Analysis", size="2", weight="bold", color=C.TEXT),
            rx.spacer(),
            rx.cond(
                AppState.selected_mail.ai.confidence_label != "",
                rx.text(
                    "信心 " + AppState.selected_mail.ai.confidence_label,
                    size="1",
                    color=C.TEXT_MUTED,
                ),
                rx.fragment(),
            ),
            spacing="2",
            align="center",
            width="100%",
            padding="10px 12px",
            background=C.PURPLE_SOFT,
            border_bottom=f"1px solid {C.PURPLE_BORDER}",
            flex_shrink="0",
        ),
        rx.cond(
            AppState.has_selection,
            rx.fragment(
                _tab_bar(),
                rx.box(
                    rx.cond(
                        AppState.selected_mail.ai.has_analysis,
                        rx.match(
                            AppState.ai_tab,
                            (TAB_SUMMARY, _summary_tab()),
                            (TAB_TODO, _todo_tab()),
                            (TAB_RECOMMEND, _recommend_tab()),
                            (TAB_REPLY, _reply_tab()),
                            _summary_tab(),
                        ),
                        _no_analysis(),
                    ),
                    flex="1",
                    overflow_y="auto",
                    min_height="0",
                    padding="12px",
                    background=C.BG,
                ),
            ),
            empty_state(
                "尚未選擇郵件",
                "選取郵件後這裡會顯示 AI 分析結果",
                icon="sparkles",
                height="100%",
            ),
        ),
        width="100%",
        height="100%",
    )
