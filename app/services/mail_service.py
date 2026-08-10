"""郵件業務邏輯。

Repository 只負責「把資料變成 Model」，
MailService 負責「這些 Model 要怎麼被使用」——分類、篩選、搜尋、統計。

上層（State / UI）不做任何資料判斷，只呼叫這裡的方法。
例如 UI 不應該自己寫 ``mail.ai.importance >= 4``，
而是呼叫 ``mail_service.get_important_mails()``；
未來重要度的定義改變時，只需要修改這一個檔案。
"""

from __future__ import annotations

from datetime import date
from typing import Callable, Dict, List, Optional

from ..models import Mail, MailCategory, MailFilter, NavKey, SystemAlert, TodoItem
from ..repositories import BaseMailRepository
from ..utils import parse_iso_date, start_of_week

#: 重要郵件的門檻（星等）。
IMPORTANT_THRESHOLD = 4


class MailService:
    """郵件查詢與統計。"""

    def __init__(
        self, repository: BaseMailRepository, today: Optional[date] = None
    ) -> None:
        self._repo = repository
        self._today_override = today

    @property
    def _today(self) -> date:
        """「今天」是哪一天。

        刻意做成 property 而不是在建構時算好：
        使用者切換檢視日期後，Repository 的 reference_date 會改變，
        所有統計必須立刻跟著變，不能沿用建構當下的值。
        """
        return self._today_override or self._repo.reference_date

    @property
    def today(self) -> date:
        """對外公開的「今天」，供 DashboardService 共用同一個基準。"""
        return self._today

    # ------------------------------------------------------------------
    # 基本存取
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        """要求資料來源重新載入（Header 的「更新郵件」）。"""
        self._repo.refresh()

    def get_all_mails(self) -> List[Mail]:
        return self._repo.get_all_mails()

    def get_mail(self, mail_id: str) -> Optional[Mail]:
        return self._repo.get_mail(mail_id)

    def get_ai_analysis(self, mail_id: str):
        return self._repo.get_ai_analysis(mail_id)

    def get_system_alerts(self) -> List[SystemAlert]:
        return self._repo.get_system_alerts()

    def get_daily_brief(self):
        return self._repo.get_daily_brief()

    def mark_as_read(self, mail_id: str) -> None:
        self._repo.mark_as_read(mail_id)

    @property
    def source_name(self) -> str:
        return self._repo.source_name

    @property
    def last_update_label(self) -> str:
        return self._repo.last_update_label

    def health_check(self) -> str:
        return self._repo.health_check()

    # ------------------------------------------------------------------
    # 日期切換
    # ------------------------------------------------------------------
    def get_available_dates(self) -> List[date]:
        """資料來源有哪幾天的資料，新到舊。空 list 代表不支援切換。"""
        return self._repo.available_dates

    def get_selected_date(self) -> Optional[date]:
        return self._repo.selected_date

    def select_date(self, value: date) -> None:
        """切換檢視日期。"""
        self._repo.select_date(value)

    # ------------------------------------------------------------------
    # 時間切分
    # ------------------------------------------------------------------
    def _sent_date(self, mail: Mail) -> Optional[date]:
        return parse_iso_date(mail.sent_at)

    def get_today_mails(self) -> List[Mail]:
        """今天收到的郵件。"""
        return [m for m in self.get_all_mails() if self._sent_date(m) == self._today]

    def get_yesterday_mails(self) -> List[Mail]:
        return [
            m
            for m in self.get_all_mails()
            if (d := self._sent_date(m)) is not None and (self._today - d).days == 1
        ]

    def get_week_mails(self) -> List[Mail]:
        """本週（週一起算）的郵件。"""
        monday = start_of_week(self._today)
        return [
            m
            for m in self.get_all_mails()
            if (d := self._sent_date(m)) is not None and d >= monday
        ]

    # ------------------------------------------------------------------
    # 分類切分
    # ------------------------------------------------------------------
    def get_action_items(self) -> List[Mail]:
        """需要本人處理的郵件。

        排序原則：先看期限（越急越前面），期限相同再看重要度。
        """
        mails = [m for m in self.get_all_mails() if m.ai.action_required]
        return sorted(mails, key=lambda m: (m.ai.deadline_days_left, -m.ai.importance))

    def get_important_mails(self) -> List[Mail]:
        return [
            m for m in self.get_all_mails() if m.ai.importance >= IMPORTANT_THRESHOLD
        ]

    def get_key_person_mails(self) -> List[Mail]:
        return [m for m in self.get_all_mails() if m.sender.is_key_person]

    def get_mails_by_category(self, category: str) -> List[Mail]:
        return [m for m in self.get_all_mails() if m.ai.category == category]

    def get_alert_mails(self) -> List[Mail]:
        return self.get_mails_by_category(MailCategory.ALERT)

    def get_report_mails(self) -> List[Mail]:
        return self.get_mails_by_category(MailCategory.REPORT)

    def get_info_mails(self) -> List[Mail]:
        return self.get_mails_by_category(MailCategory.INFO)

    def get_auto_mails(self) -> List[Mail]:
        return self.get_mails_by_category(MailCategory.AUTO)

    def get_todo_mails(self) -> List[Mail]:
        """含有 AI 拆解待辦的郵件。"""
        return [m for m in self.get_all_mails() if m.ai.todos]

    # ------------------------------------------------------------------
    # 導覽
    # ------------------------------------------------------------------
    def get_mails_for_nav(self, nav_key: str) -> List[Mail]:
        """Sidebar 的 nav key → 該顯示哪些郵件。

        「這個 key 代表什麼」的知識只存在於這裡，
        Sidebar 與 Page 都不需要知道。
        """
        resolvers: Dict[str, Callable[[], List[Mail]]] = {
            NavKey.TODAY: self.get_today_mails,
            NavKey.INBOX_ACTION: self.get_action_items,
            NavKey.INBOX_IMPORTANT: self.get_important_mails,
            NavKey.INBOX_TODO: self.get_todo_mails,
            NavKey.INBOX_ALERT: self.get_alert_mails,
            NavKey.INBOX_KEYPERSON: self.get_key_person_mails,
            NavKey.INBOX_REPORT: self.get_report_mails,
            NavKey.INBOX_INFO: self.get_info_mails,
            NavKey.INBOX_AUTO: self.get_auto_mails,
            NavKey.TIME_YESTERDAY: self.get_yesterday_mails,
            NavKey.TIME_WEEK: self.get_week_mails,
            NavKey.TIME_HISTORY: self.get_all_mails,
        }
        resolver = resolvers.get(nav_key, self.get_all_mails)
        return resolver()

    def get_nav_counts(self) -> Dict[str, int]:
        """Sidebar 每個項目要顯示的數字。

        key 對應 navigation.NavItem.counter。
        """
        mails = self.get_all_mails()
        return {
            "action": sum(1 for m in mails if m.ai.action_required),
            "important": sum(
                1 for m in mails if m.ai.importance >= IMPORTANT_THRESHOLD
            ),
            "todo": sum(len(m.ai.todos) for m in mails),
            "alert": sum(
                1 for a in self.get_system_alerts() if a.status in ("open", "monitoring")
            ),
            "keyperson": sum(1 for m in mails if m.sender.is_key_person),
            "report": sum(1 for m in mails if m.ai.category == MailCategory.REPORT),
            "info": sum(1 for m in mails if m.ai.category == MailCategory.INFO),
            "auto": sum(1 for m in mails if m.ai.category == MailCategory.AUTO),
        }

    # ------------------------------------------------------------------
    # 搜尋 / 篩選
    # ------------------------------------------------------------------
    def filter_mails(
        self,
        mails: List[Mail],
        keyword: str = "",
        filter_key: str = MailFilter.ALL,
    ) -> List[Mail]:
        """套用 Mail List 上方的搜尋與 Filter。"""
        result = mails

        if filter_key and filter_key != MailFilter.ALL:
            result = [m for m in result if self._match_filter(m, filter_key)]

        text = (keyword or "").strip().lower()
        if text:
            result = [m for m in result if self._match_keyword(m, text)]

        return result

    @staticmethod
    def _match_filter(mail: Mail, filter_key: str) -> bool:
        if filter_key == MailFilter.IMPORTANT:
            return mail.ai.importance >= IMPORTANT_THRESHOLD
        if filter_key == MailFilter.ACTION:
            return mail.ai.action_required
        if filter_key == MailFilter.ALERT:
            return mail.ai.category == MailCategory.ALERT
        if filter_key == MailFilter.REPORT:
            return mail.ai.category == MailCategory.REPORT
        return True

    @staticmethod
    def _match_keyword(mail: Mail, text: str) -> bool:
        """搜尋範圍：主旨、寄件者、AI 摘要、內文純文字。"""
        haystack = [
            mail.subject,
            mail.sender.name,
            mail.sender.email,
            mail.preview,
            mail.ai.summary,
            mail.ai.category_label,
        ]
        haystack.extend(b.text for b in mail.content_blocks if b.block_type == "text")
        haystack.extend(a.filename for a in mail.attachments)
        return any(text in (h or "").lower() for h in haystack)

    # ------------------------------------------------------------------
    # 待辦
    # ------------------------------------------------------------------
    def get_todos(self) -> List[TodoItem]:
        """所有郵件的待辦展開成單一清單。

        排序：有期限的在前（越早越前面），其次依來源郵件時間新到舊。
        """
        todos: List[TodoItem] = []
        for mail in self.get_all_mails():
            todos.extend(mail.ai.todos)
        return sorted(
            todos,
            key=lambda t: (
                t.deadline_label == "",   # 無期限的排後面
                t.deadline_label,
                t.todo_id,
            ),
        )

    def get_deadline_mails(self) -> List[Mail]:
        """有期限的郵件，依剩餘天數由少到多。"""
        mails = [m for m in self.get_all_mails() if m.ai.has_deadline]
        return sorted(mails, key=lambda m: m.ai.deadline_days_left)
