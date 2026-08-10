"""Sidebar 導覽定義。

把「有哪些導覽項目、各自對應哪個路由與標題」集中在這裡，
Sidebar Component 只負責畫，不負責決定內容。

每個項目的 nav key 來自 models.enums.NavKey，
實際「這個 key 代表哪些郵件」由 MailService 決定（見 services/mail_service.py）。
"""

from __future__ import annotations

import dataclasses
from typing import List, Optional

from .models import NavKey


@dataclasses.dataclass(frozen=True)
class NavItem:
    """單一導覽項目。"""

    key: str
    label: str
    icon: str          # lucide icon 名稱
    route: str
    title: str = ""    # 頁面主標題，空字串時使用 label
    subtitle: str = ""
    counter: str = ""  # 對應 MailService.get_nav_counts() 的 key，空字串代表不顯示數字


@dataclasses.dataclass(frozen=True)
class NavGroup:
    """導覽分組。"""

    label: str
    items: List[NavItem]


NAV_GROUPS: List[NavGroup] = [
    NavGroup(
        label="今日",
        items=[
            NavItem(
                key=NavKey.TODAY,
                label="今日總覽",
                icon="layout-dashboard",
                route="/",
                title="今日總覽",
                subtitle="AI 已為您整理今天需要關注的重點",
            ),
        ],
    ),
    NavGroup(
        label="智慧收件匣",
        items=[
            NavItem(
                key=NavKey.INBOX_ACTION,
                label="需要處理",
                icon="circle-alert",
                route="/mail/action",
                title="需要處理",
                subtitle="AI 判定需要您本人回覆或採取行動的郵件",
                counter="action",
            ),
            NavItem(
                key=NavKey.INBOX_IMPORTANT,
                label="重要郵件",
                icon="star",
                route="/mail/important",
                title="重要郵件",
                subtitle="重要度 4 星以上的郵件",
                counter="important",
            ),
            NavItem(
                key=NavKey.INBOX_TODO,
                label="待辦事項",
                icon="list-checks",
                route="/todo",
                title="待辦事項",
                subtitle="AI 從郵件內容拆解出的行動項目",
                counter="todo",
            ),
            NavItem(
                key=NavKey.INBOX_ALERT,
                label="系統 / 設備告警",
                icon="triangle-alert",
                route="/alerts",
                title="系統 / 設備事件",
                subtitle="設備異常與系統告警彙整",
                counter="alert",
            ),
            NavItem(
                key=NavKey.INBOX_KEYPERSON,
                label="主管 / 關鍵窗口",
                icon="user-round",
                route="/mail/keyperson",
                title="主管 / 關鍵窗口",
                subtitle="來自主管與關鍵窗口的郵件",
                counter="keyperson",
            ),
            NavItem(
                key=NavKey.INBOX_REPORT,
                label="報表 / Daily Report",
                icon="file-bar-chart",
                route="/reports",
                title="報表 / Daily Report",
                subtitle="每日產出、品質與設備稼動報表",
                counter="report",
            ),
            NavItem(
                key=NavKey.INBOX_INFO,
                label="一般資訊",
                icon="info",
                route="/mail/info",
                title="一般資訊",
                subtitle="不需立即處理的一般性郵件",
                counter="info",
            ),
            NavItem(
                key=NavKey.INBOX_AUTO,
                label="自動通知",
                icon="bot",
                route="/mail/auto",
                title="自動通知",
                subtitle="系統自動發送的通知信",
                counter="auto",
            ),
        ],
    ),
    NavGroup(
        label="時間",
        items=[
            NavItem(
                key=NavKey.TIME_YESTERDAY,
                label="昨日",
                icon="calendar-minus",
                route="/mail/yesterday",
                title="昨日郵件",
                subtitle="",
            ),
            NavItem(
                key=NavKey.TIME_WEEK,
                label="本週",
                icon="calendar-range",
                route="/mail/week",
                title="本週郵件",
                subtitle="",
            ),
            NavItem(
                key=NavKey.TIME_HISTORY,
                label="歷史郵件",
                icon="archive",
                route="/mail/history",
                title="歷史郵件",
                subtitle="全部郵件",
            ),
        ],
    ),
    NavGroup(
        label="AI",
        items=[
            NavItem(
                key=NavKey.ASK_AI,
                label="Ask AI",
                icon="sparkles",
                route="/ask-ai",
                title="Ask AI",
                subtitle="用自然語言查詢今天的郵件與待辦",
            ),
        ],
    ),
]


#: 設定放在 Sidebar 最底部，與上面的分組分開顯示。
SETTINGS_ITEM = NavItem(
    key=NavKey.SETTINGS,
    label="設定",
    icon="settings",
    route="/settings",
    title="設定",
    subtitle="資料來源與系統資訊",
)


ALL_ITEMS: List[NavItem] = [
    item for group in NAV_GROUPS for item in group.items
] + [SETTINGS_ITEM]

_BY_KEY = {item.key: item for item in ALL_ITEMS}
_BY_ROUTE = {item.route: item for item in ALL_ITEMS}


def get_item(nav_key: str) -> Optional[NavItem]:
    """依 nav key 取得導覽項目。"""
    return _BY_KEY.get(nav_key)


def get_item_by_route(route: str) -> Optional[NavItem]:
    """依路由取得導覽項目。"""
    return _BY_ROUTE.get(route)
