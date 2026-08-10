"""Dashboard 業務邏輯。

首頁的所有數字都在這裡由實際資料計算，
UI 只負責顯示 KpiSummary 的欄位，不做任何加總或判斷。
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from ..models import (
    DashboardSummary,
    KpiSummary,
    Mail,
    MailCategory,
    SystemAlert,
)
from ..utils import fmt_today_header
from .mail_service import IMPORTANT_THRESHOLD, MailService

#: 首頁「需要您處理」最多顯示幾張卡片。
ACTION_CARD_LIMIT = 5

#: 首頁「系統 / 設備事件」最多顯示幾張卡片。
ALERT_CARD_LIMIT = 4

#: 視為「進行中」的事件狀態。
_ACTIVE_ALERT_STATUS = ("open", "monitoring")


class DashboardService:
    """今日總覽的資料組裝。"""

    def __init__(self, mail_service: MailService, today: Optional[date] = None) -> None:
        self._mails = mail_service
        self._today_override = today

    @property
    def _today(self) -> date:
        """與 MailService 共用同一個「今天」，切換日期後會立即反映。"""
        return self._today_override or self._mails.today

    # ------------------------------------------------------------------
    # KPI
    # ------------------------------------------------------------------
    def get_kpi_summary(self) -> KpiSummary:
        """計算首頁最上方的 KPI 數字。

        「今日郵件 / 重要郵件 / 一般資訊」以今天為範圍，
        「待辦事項 / 系統事件」則是目前所有未結案的量，
        因為這兩者的價值在於「還沒做完」而不是「今天收到」。
        """
        today_mails = self._mails.get_today_mails()
        all_mails = self._mails.get_all_mails()
        alerts = self._mails.get_system_alerts()

        todos = [t for m in all_mails for t in m.ai.todos]

        return KpiSummary(
            total_today=len(today_mails),
            important=sum(
                1 for m in today_mails if m.ai.importance >= IMPORTANT_THRESHOLD
            ),
            todo=sum(1 for t in todos if not t.done),
            system_events=sum(1 for a in alerts if a.status in _ACTIVE_ALERT_STATUS),
            general_info=sum(
                1
                for m in today_mails
                if m.ai.category in (MailCategory.INFO, MailCategory.AUTO)
            ),
            unread_today=sum(1 for m in today_mails if not m.is_read),
            overdue=sum(1 for m in all_mails if m.ai.is_overdue),
            due_soon=sum(1 for m in all_mails if m.ai.is_due_soon),
            resolved_alerts=sum(1 for a in alerts if a.status not in _ACTIVE_ALERT_STATUS),
        )

    # ------------------------------------------------------------------
    # 區塊
    # ------------------------------------------------------------------
    def get_action_mails(self, limit: int = ACTION_CARD_LIMIT) -> List[Mail]:
        """「需要您處理」卡片。"""
        return self._mails.get_action_items()[:limit]

    def get_active_alerts(self, limit: int = ALERT_CARD_LIMIT) -> List[SystemAlert]:
        """「系統 / 設備事件」卡片：未結案的排前面。"""
        alerts = self._mails.get_system_alerts()
        active = [a for a in alerts if a.status in _ACTIVE_ALERT_STATUS]
        closed = [a for a in alerts if a.status not in _ACTIVE_ALERT_STATUS]
        return (active + closed)[:limit]

    # ------------------------------------------------------------------
    # 一次取得全部
    # ------------------------------------------------------------------
    def get_dashboard_summary(self) -> DashboardSummary:
        """首頁需要的所有資料，一次組好給 State。"""
        return DashboardSummary(
            kpi=self.get_kpi_summary(),
            brief=self._mails.get_daily_brief(),
            action_mails=self.get_action_mails(),
            alerts=self.get_active_alerts(),
            today_label=fmt_today_header(self._today),
            last_update_label=self._mails.last_update_label,
        )
