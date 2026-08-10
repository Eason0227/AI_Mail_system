"""Repository 介面定義。

這份介面是 UI 與資料來源之間的合約。
不論資料來自 Mock JSON、Lotus Notes、公司 API 或 SQLite，
只要實作這個介面，上層（Service / State / UI）完全不需要修改。

回傳型別一律是 app.models 內的內部模型，不可以回傳原始 dict。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import List, Optional

from ..models import AIAnalysis, DailyBrief, Mail, SystemAlert


class BaseMailRepository(ABC):
    """郵件資料來源介面。"""

    #: 顯示在 UI 上的資料來源名稱，例如 "Mock Data" / "Lotus Notes"
    source_name: str = "Unknown"

    # ------------------------------------------------------------------
    # 郵件
    # ------------------------------------------------------------------
    @abstractmethod
    def get_all_mails(self) -> List[Mail]:
        """取得所有郵件（已附帶 AI 分析結果），依時間新到舊排序。"""

    @abstractmethod
    def get_mail(self, mail_id: str) -> Optional[Mail]:
        """依 ID 取得單封郵件，找不到回傳 None。"""

    @abstractmethod
    def get_ai_analysis(self, mail_id: str) -> Optional[AIAnalysis]:
        """取得單封郵件的 AI 分析結果。"""

    # ------------------------------------------------------------------
    # 系統事件 / 每日摘要
    # ------------------------------------------------------------------
    @abstractmethod
    def get_system_alerts(self) -> List[SystemAlert]:
        """取得系統 / 設備事件清單。"""

    @abstractmethod
    def get_daily_brief(self) -> DailyBrief:
        """取得 AI 今日重點摘要。"""

    # ------------------------------------------------------------------
    # 狀態變更
    # ------------------------------------------------------------------
    @abstractmethod
    def mark_as_read(self, mail_id: str) -> None:
        """標記為已讀。

        Mock 階段只改記憶體內的狀態；
        公司環境可視需求寫回 Lotus Notes 或本地狀態檔。
        """

    @abstractmethod
    def refresh(self) -> None:
        """重新載入資料來源（對應 Header 的「更新郵件」按鈕）。"""

    # ------------------------------------------------------------------
    # 診斷
    # ------------------------------------------------------------------
    def health_check(self) -> str:
        """回傳資料來源狀態描述，供設定頁顯示。預設不做任何檢查。"""
        return "OK"

    @property
    def last_update_label(self) -> str:
        """資料最後更新時間的顯示字串，供 Header 的 Last Update 使用。

        由 Repository 提供而非 UI 自己取現在時間，
        因為「資料何時更新」只有資料來源知道。
        """
        return ""

    # ------------------------------------------------------------------
    # 日期切換
    # ------------------------------------------------------------------
    @property
    def available_dates(self) -> List[date]:
        """這個資料來源有哪幾天的資料，新到舊排序。

        回傳空 list 代表「不支援日期切換」，UI 會隱藏日期選擇器。
        Mock 會把資料平移到當天，因此維持預設即可。
        """
        return []

    @property
    def selected_date(self) -> Optional[date]:
        """目前正在檢視哪一天。不支援切換時回傳 None。"""
        return None

    def select_date(self, value: date) -> None:
        """切換到指定日期並重新載入。預設不支援，什麼都不做。"""

    @property
    def reference_date(self) -> date:
        """這份資料的「今天」是哪一天。

        Service 的「今日郵件」「昨日」「本週」都以這個日期為基準，
        而不是直接用系統日期。

        原因：公司 pipeline 是「指定日期批次執行」的，
        在 8/10 檢視 8/07 那批資料時，「今日總覽」應該指 8/07，
        否則整個首頁會是空的。

        Mock 會把資料平移到系統當天，所以維持預設即可。
        """
        return date.today()
