"""設定頁。

主要用途是把「目前資料從哪裡來」攤開來給使用者看，
也是第二階段切換到公司環境時的第一個檢查點。
"""

from __future__ import annotations

import reflex as rx

from .. import config
from ..components import (
    card,
    page_layout,
    page_title_bar,
    pill,
    section_header,
    toolbar_button,
)
from ..states import AppState
from ..theme import C, S


def _row(label: str, value, mono: bool = False) -> rx.Component:
    return rx.hstack(
        rx.text(label, size="2", color=C.TEXT_MUTED, width="180px", flex_shrink="0"),
        rx.text(
            value,
            size="2",
            color=C.TEXT,
            weight="medium",
            font_family="ui-monospace, SFMono-Regular, monospace" if mono else "inherit",
            word_break="break-all",
        ),
        spacing="3",
        align="start",
        width="100%",
        padding="8px 0",
        border_bottom=f"1px solid {C.BORDER}",
    )


def _data_source() -> rx.Component:
    return rx.vstack(
        section_header(
            "資料來源",
            icon="database",
            action=toolbar_button(
                "重新載入", icon="refresh-cw", on_click=AppState.reload_data_source
            ),
        ),
        rx.hstack(
            rx.text("DATA_MODE", size="2", color=C.TEXT_MUTED, width="180px"),
            rx.cond(
                AppState.data_mode == "mock",
                pill(
                    "mock",
                    fg=C.WARNING,
                    bg=C.WARNING_SOFT,
                    border=C.WARNING_BORDER,
                    icon="flask-conical",
                ),
                pill(
                    "real",
                    fg=C.SUCCESS,
                    bg=C.SUCCESS_SOFT,
                    border=C.SUCCESS_BORDER,
                    icon="building-2",
                ),
            ),
            spacing="3",
            align="center",
            width="100%",
            padding="8px 0",
            border_bottom=f"1px solid {C.BORDER}",
        ),
        _row("Repository", AppState.source_name),
        _row("狀態", AppState.health_text),
        _row("最後更新", AppState.last_update_label),
        _row("Mock 資料目錄", str(config.MOCK_DATA_DIR), mono=True),
        _row("公司資料目錄（第二階段）", str(config.REAL_DATA_DIR), mono=True),
        _row("附件 / 圖片 URL 前綴", config.ASSET_URL_PREFIX, mono=True),
        _row("Mock 日期平移", "開啟" if config.MOCK_SHIFT_DATES else "關閉"),
        spacing="0",
        width="100%",
        align="start",
    )


def _identity_section() -> rx.Component:
    """使用者身分與關鍵窗口設定的來源。"""
    keywords = config.KEY_PERSON_KEYWORDS
    return rx.vstack(
        section_header("使用者身分", icon="user-round"),
        _row("姓名", config.CURRENT_USER.get("name", "")),
        _row("角色", config.CURRENT_USER.get("role", "")),
        _row("Email", config.CURRENT_USER.get("email", ""), mono=True),
        _row(
            "主管 / 關鍵窗口",
            "、".join(keywords) if keywords else "（未設定，此分類會是 0 封）",
        ),
        _row("設定來源", str(config.COMPANY_CONFIG_PATH), mono=True),
        rx.text(
            "身分沿用公司 pipeline 的 user_identity，不在 Dashboard 重複維護。"
            "可用環境變數 MAIL_DASHBOARD_USER_NAME / _ROLE / _EMAIL "
            "與 MAIL_DASHBOARD_KEY_PERSONS 覆蓋。",
            size="1",
            color=C.TEXT_MUTED,
            line_height="1.7",
            margin_top="8px",
        ),
        spacing="0",
        width="100%",
        align="start",
    )


def _ai_section() -> rx.Component:
    return rx.vstack(
        section_header("AI", icon="sparkles"),
        _row("AI_MODE", AppState.ai_mode),
        _row(
            "Ask AI 引擎",
            rx.cond(
                AppState.ai_mode == "mock",
                "MockRuleAskAIEngine（本機規則比對，不呼叫外部 API）",
                "LlmAskAIEngine",
            ),
        ),
        _row("回覆草稿來源", rx.cond(AppState.ai_mode == "mock", "Mock reply_draft", "LLM")),
        spacing="0",
        width="100%",
        align="start",
    )


def _stage_note() -> rx.Component:
    """把兩階段的切換方式寫在畫面上，避免之後忘記。"""
    return rx.vstack(
        section_header("切換到公司環境", icon="arrow-right-left"),
        rx.text(
            "第二階段只需要以下兩步，UI / Component / State 完全不需要修改：",
            size="2",
            color=C.TEXT_SECONDARY,
            line_height="1.8",
        ),
        rx.vstack(
            *[
                rx.hstack(
                    rx.center(
                        rx.text(
                            str(i + 1),
                            size="1",
                            weight="bold",
                            color=C.PRIMARY,
                            line_height="1",
                        ),
                        background=C.PRIMARY_SOFT,
                        border_radius=S.RADIUS_PILL,
                        width="20px",
                        height="20px",
                        flex_shrink="0",
                        margin_top="2px",
                    ),
                    rx.text(text, size="2", color=C.TEXT, line_height="1.7"),
                    spacing="3",
                    align="start",
                    width="100%",
                )
                for i, text in enumerate(
                    [
                        "把 app/config.py 的 DATA_MODE 改成 \"real\""
                        "（或設定環境變數 MAIL_DASHBOARD_DATA_MODE=real）。",
                        "在 app/repositories/real_mail_repository.py 內，"
                        "依公司實際的 JSON Schema 完成 CompanyMailAdapter 與 _load_raw()。",
                    ]
                )
            ],
            spacing="2",
            width="100%",
        ),
        rx.text(
            "Adapter 的寫法可直接參考 app/repositories/adapters/mock_adapter.py，"
            "它已經示範完整的欄位改名、單位換算與顯示值計算。",
            size="1",
            color=C.TEXT_MUTED,
            line_height="1.7",
        ),
        spacing="3",
        width="100%",
        align="start",
    )


def settings_page() -> rx.Component:
    return page_layout(
        page_title_bar(),
        card(_data_source()),
        card(_identity_section()),
        card(_ai_section()),
        card(_stage_note()),
    )
