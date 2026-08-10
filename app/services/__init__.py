"""業務邏輯層。

State 只跟這一層說話，不直接碰 Repository，也不知道 Mock / Real 的差別。

    State  ->  services.mail_service / dashboard_service / ask_ai_service
                       |
                       v
               repositories.get_mail_repository()
"""

from __future__ import annotations

from typing import Optional

from ..repositories import get_mail_repository, reset_mail_repository
from .ai_service import AskAIService
from .dashboard_service import DashboardService
from .mail_service import MailService

_mail_service: Optional[MailService] = None
_dashboard_service: Optional[DashboardService] = None
_ask_ai_service: Optional[AskAIService] = None


def get_mail_service() -> MailService:
    """取得郵件 Service 單例。

    不傳 today：「今天」由 Repository 的 reference_date 動態決定，
    使用者切換檢視日期後統計才會跟著變。
    """
    global _mail_service
    if _mail_service is None:
        _mail_service = MailService(get_mail_repository())
    return _mail_service


def get_dashboard_service() -> DashboardService:
    """取得 Dashboard Service 單例。"""
    global _dashboard_service
    if _dashboard_service is None:
        _dashboard_service = DashboardService(get_mail_service())
    return _dashboard_service


def get_ask_ai_service() -> AskAIService:
    """取得 Ask AI Service 單例。"""
    global _ask_ai_service
    if _ask_ai_service is None:
        _ask_ai_service = AskAIService(get_mail_service())
    return _ask_ai_service


def reload_services() -> None:
    """整組重建（設定頁切換資料來源後使用）。"""
    global _mail_service, _dashboard_service, _ask_ai_service
    reset_mail_repository()
    _mail_service = None
    _dashboard_service = None
    _ask_ai_service = None


__all__ = [
    "AskAIService",
    "DashboardService",
    "MailService",
    "get_ask_ai_service",
    "get_dashboard_service",
    "get_mail_service",
    "reload_services",
]
