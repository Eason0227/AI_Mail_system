"""應用程式進入點與路由。

每個路由的 on_load 只做一件事：告訴 State「現在在哪一頁」。
「這一頁該顯示哪些郵件」由 MailService 決定（services/mail_service.py），
因此新增分類時只需要動 navigation.py 與 MailService，不必改動頁面。
"""

from __future__ import annotations

import reflex as rx

from . import config, navigation
from .models import NavKey
from .pages import (
    alerts_page,
    ask_ai_page,
    dashboard_page,
    mail_page,
    reports_page,
    settings_page,
    todo_page,
)
from .states import AppState
from .theme import C

#: 共用 Mail Workspace 版面的導覽項目。
_MAIL_WORKSPACE_NAVS = (
    NavKey.INBOX_ACTION,
    NavKey.INBOX_IMPORTANT,
    NavKey.INBOX_KEYPERSON,
    NavKey.INBOX_INFO,
    NavKey.INBOX_AUTO,
    NavKey.TIME_YESTERDAY,
    NavKey.TIME_WEEK,
    NavKey.TIME_HISTORY,
)


def _mail_asset_app():
    """提供真實郵件內嵌圖片的靜態路由。

    Mock 階段圖片放在 assets/ 底下由 Reflex 直接提供；
    公司資料的圖片在 REAL_DATA_DIR 裡（不能整包複製到 assets/），
    因此掛一個唯讀靜態路由指過去，URL 前綴為 config.REAL_ASSET_ROUTE。

    目錄不存在時回傳 None，不影響 Mock 模式啟動。
    """
    if not config.REAL_DATA_DIR.is_dir():
        return None

    from starlette.applications import Starlette
    from starlette.routing import Mount
    from starlette.staticfiles import StaticFiles

    return Starlette(
        routes=[
            Mount(
                config.REAL_ASSET_ROUTE,
                app=StaticFiles(directory=str(config.REAL_DATA_DIR)),
                name="mail_assets",
            )
        ]
    )


_asset_app = _mail_asset_app()

#: Radix 基底主題設定在 rxconfig.py 的 RadixThemesPlugin；
#: 這裡只放全站的字體與底色。
app = rx.App(
    api_transformer=_asset_app if _asset_app is not None else None,
    style={
        "font_family": (
            '"Inter", "Noto Sans TC", -apple-system, BlinkMacSystemFont, '
            '"Segoe UI", "Microsoft JhengHei", sans-serif'
        ),
        "background": C.BG,
        "color": C.TEXT,
    },
)


def _page_title(item_title: str) -> str:
    return f"{item_title}｜{config.APP_TITLE}"


# --------------------------------------------------------------------------
# 今日總覽
# --------------------------------------------------------------------------
app.add_page(
    dashboard_page,
    route="/",
    title=_page_title("今日總覽"),
    on_load=AppState.load_dashboard,
)


# --------------------------------------------------------------------------
# Mail Workspace（智慧收件匣 / 時間分類）
# --------------------------------------------------------------------------
for _nav_key in _MAIL_WORKSPACE_NAVS:
    _item = navigation.get_item(_nav_key)
    if _item is None:
        continue
    app.add_page(
        mail_page,
        route=_item.route,
        title=_page_title(_item.title or _item.label),
        on_load=AppState.load_nav(_nav_key),
    )

# /mail 直接進入時等同「歷史郵件」（全部郵件）。
app.add_page(
    mail_page,
    route="/mail",
    title=_page_title("郵件"),
    on_load=AppState.load_nav(NavKey.TIME_HISTORY),
)


# --------------------------------------------------------------------------
# 待辦 / 事件 / 報表
# --------------------------------------------------------------------------
app.add_page(
    todo_page,
    route="/todo",
    title=_page_title("待辦事項"),
    on_load=AppState.load_todos,
)

app.add_page(
    alerts_page,
    route="/alerts",
    title=_page_title("系統 / 設備事件"),
    on_load=AppState.load_alerts,
)

app.add_page(
    reports_page,
    route="/reports",
    title=_page_title("報表 / Daily Report"),
    on_load=AppState.load_nav(NavKey.INBOX_REPORT),
)


# --------------------------------------------------------------------------
# Ask AI / 設定
# --------------------------------------------------------------------------
app.add_page(
    ask_ai_page,
    route="/ask-ai",
    title=_page_title("Ask AI"),
    on_load=AppState.load_ask_ai,
)

app.add_page(
    settings_page,
    route="/settings",
    title=_page_title("設定"),
    on_load=AppState.load_settings,
)
