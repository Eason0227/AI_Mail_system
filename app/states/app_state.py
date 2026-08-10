"""全域 State。

職責邊界
--------
State 是 Service 與 UI 之間唯一的橋樑：

* 只呼叫 services/，不 import repositories/，更不知道 JSON 檔在哪裡。
* 不做業務判斷（「什麼算重要」「哪些要處理」一律問 Service）。
* 只負責「畫面現在該顯示什麼」：目前選了哪封信、開了哪個 Tab、搜尋字串是什麼。

因此第二階段換成 RealMailRepository 時，這個檔案完全不需要修改。
"""

from __future__ import annotations

import dataclasses
from datetime import date
from typing import Dict, List

import reflex as rx

from .. import config, navigation
from ..models import (
    EMPTY_MAIL,
    AskAIAnswer,
    DailyBrief,
    KpiSummary,
    Mail,
    MailFilter,
    NavKey,
    SystemAlert,
    TodoItem,
)
from ..services import (
    get_ask_ai_service,
    get_dashboard_service,
    get_mail_service,
    reload_services,
)
from ..utils import parse_iso_date

#: AI Analysis Panel 的 Tab 值。
TAB_SUMMARY = "summary"
TAB_TODO = "todo"
TAB_RECOMMEND = "recommend"
TAB_REPLY = "reply"


class AppState(rx.State):
    """整個 Dashboard 的畫面狀態。"""

    # ------------------------------------------------------------------
    # 導覽 / 外框
    # ------------------------------------------------------------------
    nav_key: str = NavKey.TODAY
    page_title: str = ""
    page_subtitle: str = ""
    nav_counts: Dict[str, int] = {}

    today_label: str = ""
    last_update_label: str = ""
    source_name: str = ""
    is_refreshing: bool = False

    # ---- 檢視日期 ----
    #: 可選日期（ISO 字串，新到舊）。空 list 代表資料來源不支援切換，UI 隱藏選擇器。
    available_dates: List[str] = []
    selected_date: str = ""
    #: 今天沒有資料而自動退回其他日期時顯示提示。
    date_fallback_note: str = ""

    # ------------------------------------------------------------------
    # 今日總覽
    # ------------------------------------------------------------------
    kpi: KpiSummary = KpiSummary()
    brief: DailyBrief = DailyBrief()
    action_mails: List[Mail] = []
    alerts: List[SystemAlert] = []
    brief_open: bool = False

    # ------------------------------------------------------------------
    # Mail Workspace
    # ------------------------------------------------------------------
    mails: List[Mail] = []
    selected_mail: Mail = EMPTY_MAIL
    search_text: str = ""
    mail_filter: str = MailFilter.ALL

    #: 從別的頁面（例如今日總覽的卡片）跳過來時，要自動選取的郵件。
    pending_mail_id: str = ""
    pending_tab: str = ""

    # ------------------------------------------------------------------
    # AI Analysis Panel
    # ------------------------------------------------------------------
    ai_tab: str = TAB_SUMMARY
    reply_draft: str = ""
    reply_generated: bool = False
    reply_generating: bool = False
    draft_saved: bool = False

    #: 資料來源沒有提供回覆草稿（公司 pipeline 目前不輸出 reply_draft）。
    #: 與「還沒產生」要分開，否則使用者會看到一個沒有說明的空白輸入框。
    reply_unavailable: bool = False

    # ------------------------------------------------------------------
    # 待辦
    # ------------------------------------------------------------------
    todos: List[TodoItem] = []
    #: 使用者在前端勾選完成的待辦。第一階段不寫回資料來源。
    done_todo_ids: List[str] = []

    # ------------------------------------------------------------------
    # Ask AI
    # ------------------------------------------------------------------
    ask_input: str = ""
    ask_answer: AskAIAnswer = AskAIAnswer()
    ask_history: List[AskAIAnswer] = []
    ask_suggestions: List[str] = []
    ask_loading: bool = False
    ask_panel_open: bool = False

    # ------------------------------------------------------------------
    # 設定頁
    # ------------------------------------------------------------------
    health_text: str = ""

    # ==================================================================
    # 載入
    # ==================================================================
    def _load_shell(self, nav_key: str) -> None:
        """所有頁面共用的外框資料（Header + Sidebar）。"""
        mail_service = get_mail_service()
        dashboard = get_dashboard_service()

        self.nav_key = nav_key
        item = navigation.get_item(nav_key)
        self.page_title = (item.title or item.label) if item else ""
        self.page_subtitle = item.subtitle if item else ""

        self.nav_counts = mail_service.get_nav_counts()
        self.source_name = mail_service.source_name
        self.last_update_label = mail_service.last_update_label
        self.today_label = dashboard.get_dashboard_summary().today_label

        self._sync_dates()

        if not self.ask_suggestions:
            self.ask_suggestions = get_ask_ai_service().suggested_questions()

    def _sync_dates(self) -> None:
        """更新可選日期與目前檢視的日期。"""
        mail_service = get_mail_service()
        dates = mail_service.get_available_dates()
        self.available_dates = [d.isoformat() for d in dates]

        current = mail_service.get_selected_date()
        self.selected_date = current.isoformat() if current else ""

        # 預設要看今天；今天沒有資料時會退回最近一天，這裡把原因說清楚。
        system_today = date.today()
        if current and dates and current != system_today:
            self.date_fallback_note = (
                f"今天（{system_today.isoformat()}）沒有資料，顯示最近的一天"
                if system_today not in dates
                else ""
            )
        else:
            self.date_fallback_note = ""

    @rx.event
    def load_dashboard(self):
        """今日總覽 on_load。"""
        summary = get_dashboard_service().get_dashboard_summary()
        self._load_shell(NavKey.TODAY)

        self.kpi = summary.kpi
        self.brief = summary.brief
        self.action_mails = summary.action_mails
        self.alerts = summary.alerts
        self.today_label = summary.today_label
        self.last_update_label = summary.last_update_label

    @rx.event
    def load_nav(self, nav_key: str):
        """Mail Workspace 類頁面的 on_load。"""
        self._load_shell(nav_key)
        self._reload_mails()

        # 從其他頁面指定要開啟的郵件優先；否則預設選第一封。
        # 指定的郵件不在目前清單裡時（例如資料已更新）退回第一封，
        # 不要讓使用者點了卡片卻看到空白面板。
        available = {m.mail_id for m in self.mails}
        fallback = self.mails[0].mail_id if self.mails else ""
        target = (
            self.pending_mail_id
            if self.pending_mail_id in available
            else fallback
        )
        if self.pending_tab:
            self.ai_tab = self.pending_tab
        else:
            self.ai_tab = TAB_SUMMARY
        self.pending_mail_id = ""
        self.pending_tab = ""

        if target:
            self._select(target)
        else:
            self.selected_mail = EMPTY_MAIL

    @rx.event
    def load_todos(self):
        """待辦事項頁 on_load。"""
        self._load_shell(NavKey.INBOX_TODO)
        self.todos = get_mail_service().get_todos()

    @rx.event
    def load_alerts(self):
        """系統 / 設備事件頁 on_load。"""
        self._load_shell(NavKey.INBOX_ALERT)
        self.alerts = get_mail_service().get_system_alerts()

    @rx.event
    def load_ask_ai(self):
        """Ask AI 頁 on_load。"""
        self._load_shell(NavKey.ASK_AI)

    @rx.event
    def load_settings(self):
        """設定頁 on_load。"""
        self._load_shell(NavKey.SETTINGS)
        self.health_text = get_mail_service().health_check()

    def _reload_mails(self) -> None:
        """依目前 nav key 重新取得郵件清單。"""
        self.mails = get_mail_service().get_mails_for_nav(self.nav_key)

    # ==================================================================
    # Header
    # ==================================================================
    @rx.event
    def change_date(self, value: str):
        """切換檢視日期。

        換日等於整份資料換掉，因此清空目前的選取與草稿狀態，
        再依目前所在頁面重新載入。
        """
        target = parse_iso_date(value)
        if target is None or value == self.selected_date:
            return

        get_mail_service().select_date(target)

        self.selected_mail = EMPTY_MAIL
        self.pending_mail_id = ""
        self.pending_tab = ""
        self.search_text = ""
        self.mail_filter = MailFilter.ALL
        self.done_todo_ids = []
        self.reply_draft = ""
        self.reply_generated = False
        self.reply_unavailable = False
        self.draft_saved = False

        return AppState.reload_current_page

    @rx.event
    def reload_current_page(self):
        """依目前所在的 nav key 重新載入該頁資料。"""
        if self.nav_key == NavKey.TODAY:
            return AppState.load_dashboard
        if self.nav_key == NavKey.INBOX_TODO:
            return AppState.load_todos
        if self.nav_key == NavKey.INBOX_ALERT:
            return AppState.load_alerts
        if self.nav_key == NavKey.ASK_AI:
            return AppState.load_ask_ai
        if self.nav_key == NavKey.SETTINGS:
            return AppState.load_settings
        return AppState.load_nav(self.nav_key)

    @rx.event
    def refresh_mails(self):
        """Header 的「更新郵件」。"""
        self.is_refreshing = True
        yield

        get_mail_service().refresh()

        if self.nav_key in (NavKey.TODAY, NavKey.INBOX_TODO, NavKey.INBOX_ALERT):
            yield AppState.reload_current_page
        else:
            selected = self.selected_mail.mail_id
            self._load_shell(self.nav_key)
            self._reload_mails()
            if selected:
                self._select(selected)

        self.is_refreshing = False

    # ==================================================================
    # Mail List
    # ==================================================================
    @rx.var
    def visible_mails(self) -> List[Mail]:
        """套用搜尋與 Filter 之後要顯示的郵件。

        判斷邏輯在 MailService，State 只負責把目前的條件傳過去。
        """
        return get_mail_service().filter_mails(
            self.mails, self.search_text, self.mail_filter
        )

    @rx.var
    def visible_mail_count(self) -> int:
        return len(self.visible_mails)

    @rx.var
    def has_mails(self) -> bool:
        return len(self.visible_mails) > 0

    @rx.var
    def has_selection(self) -> bool:
        return self.selected_mail.mail_id != ""

    @rx.event
    def on_search_change(self, value: str):
        self.search_text = value

    @rx.event
    def clear_search(self):
        self.search_text = ""

    @rx.event
    def set_filter(self, filter_key: str):
        self.mail_filter = filter_key

    @rx.event
    def select_mail(self, mail_id: str):
        """點選郵件：切換右側面板並標記已讀。"""
        self._select(mail_id, mark_read=True)
        self.ai_tab = TAB_SUMMARY

    def _select(self, mail_id: str, mark_read: bool = False) -> None:
        service = get_mail_service()
        if mark_read:
            service.mark_as_read(mail_id)
            self._reload_mails()

        mail = service.get_mail(mail_id)
        self.selected_mail = mail if mail is not None else EMPTY_MAIL

        # 換一封信就重置回覆草稿的狀態。
        self.reply_draft = ""
        self.reply_generated = False
        self.reply_unavailable = False
        self.draft_saved = False

    # ==================================================================
    # 跨頁開信
    # ==================================================================
    @rx.event
    def open_mail(self, mail_id: str, tab: str = TAB_SUMMARY):
        """從今日總覽 / 事件頁跳到 Mail Workspace 並選取指定郵件。"""
        if not mail_id:
            return None
        self.pending_mail_id = mail_id
        self.pending_tab = tab
        return rx.redirect("/mail/history")

    @rx.event
    def open_mail_summary(self, mail_id: str):
        return AppState.open_mail(mail_id, TAB_SUMMARY)

    @rx.event
    def open_mail_original(self, mail_id: str):
        return AppState.open_mail(mail_id, TAB_SUMMARY)

    @rx.event
    def open_mail_reply(self, mail_id: str):
        return AppState.open_mail(mail_id, TAB_REPLY)

    # ==================================================================
    # AI Analysis Panel
    # ==================================================================
    @rx.event
    def set_ai_tab(self, tab: str):
        self.ai_tab = tab

    @rx.event
    def generate_reply(self):
        """產生回覆草稿。

        第一階段由 AskAIService 讀 Mock 的 reply_draft，
        第二階段同一個呼叫會改成 LLM 產生，這裡不需要修改。
        """
        mail_id = self.selected_mail.mail_id
        if not mail_id:
            return

        self.reply_generating = True
        self.draft_saved = False
        self.reply_unavailable = False
        yield

        draft = get_ask_ai_service().generate_reply_draft(mail_id)
        self.reply_draft = draft
        # 草稿是空的代表資料來源根本沒有這個欄位，不是產生失敗。
        self.reply_generated = bool(draft)
        self.reply_unavailable = not draft
        self.reply_generating = False

    @rx.event
    def regenerate_reply(self):
        self.reply_generated = False
        self.reply_unavailable = False
        self.reply_draft = ""
        return AppState.generate_reply

    @rx.event
    def on_reply_change(self, value: str):
        """使用者直接修改草稿。"""
        self.reply_draft = value
        self.draft_saved = False

    @rx.event
    def copy_reply(self):
        """複製草稿到剪貼簿。"""
        return rx.set_clipboard(self.reply_draft)

    @rx.event
    def save_draft(self):
        """建立 Draft。

        **第一階段不實作真正寄信，也不寫回 Lotus Notes。**
        只在畫面上標記「已建立草稿」。
        """
        self.draft_saved = True

    @rx.var
    def has_reply_draft(self) -> bool:
        return self.reply_draft != ""

    # ==================================================================
    # 待辦
    # ==================================================================
    @rx.event
    def toggle_todo(self, todo_id: str):
        """勾選 / 取消待辦。第一階段只存在前端 State。"""
        if todo_id in self.done_todo_ids:
            self.done_todo_ids = [t for t in self.done_todo_ids if t != todo_id]
        else:
            self.done_todo_ids = self.done_todo_ids + [todo_id]

    def _apply_done(self, todos: List[TodoItem]) -> List[TodoItem]:
        """把前端的完成狀態套進待辦清單。"""
        done = set(self.done_todo_ids)
        return [
            dataclasses.replace(t, done=t.done or t.todo_id in done) for t in todos
        ]

    @rx.var
    def visible_todos(self) -> List[TodoItem]:
        """待辦事項頁的清單：未完成在前。"""
        applied = self._apply_done(self.todos)
        return sorted(applied, key=lambda t: t.done)

    @rx.var
    def selected_todos(self) -> List[TodoItem]:
        """AI Analysis Panel 內、目前這封信的待辦。"""
        return self._apply_done(self.selected_mail.ai.todos)

    @rx.var
    def todo_done_count(self) -> int:
        return sum(1 for t in self.visible_todos if t.done)

    @rx.var
    def todo_open_count(self) -> int:
        return len(self.todos) - self.todo_done_count

    @rx.var
    def kpi_todo_display(self) -> int:
        """KPI 的待辦數量會扣掉使用者剛勾掉的項目。"""
        return max(0, self.kpi.todo - len(self.done_todo_ids))

    # ==================================================================
    # Ask AI
    # ==================================================================
    @rx.event
    def on_ask_change(self, value: str):
        self.ask_input = value

    @rx.event
    def ask(self):
        """送出問題。"""
        question = self.ask_input.strip()
        if not question:
            return

        self.ask_loading = True
        self.ask_panel_open = True
        yield

        answer = get_ask_ai_service().ask(question)
        self.ask_answer = answer
        self.ask_history = [answer] + self.ask_history
        self.ask_input = ""
        self.ask_loading = False

    @rx.event
    def ask_suggested(self, question: str):
        self.ask_input = question
        return AppState.ask

    @rx.event
    def close_ask_panel(self):
        self.ask_panel_open = False

    @rx.event
    def clear_ask_history(self):
        self.ask_history = []
        self.ask_answer = AskAIAnswer()

    @rx.var
    def has_ask_answer(self) -> bool:
        return self.ask_answer.question != ""

    @rx.var
    def has_ask_history(self) -> bool:
        return len(self.ask_history) > 0

    # ==================================================================
    # 今日重點
    # ==================================================================
    @rx.event
    def open_brief(self):
        self.brief_open = True

    @rx.event
    def set_brief_open(self, value: bool):
        self.brief_open = value

    # ==================================================================
    # 設定
    # ==================================================================
    @rx.event
    def reload_data_source(self):
        """重新建立 Repository 與 Service（設定頁）。"""
        reload_services()
        self.health_text = get_mail_service().health_check()
        self._load_shell(NavKey.SETTINGS)

    @rx.var
    def data_mode(self) -> str:
        return config.DATA_MODE

    @rx.var
    def ai_mode(self) -> str:
        return config.AI_MODE

    @rx.var
    def show_mock_badge(self) -> bool:
        return config.SHOW_MOCK_BADGE
