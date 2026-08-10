"""系統內部使用的分類常數。

重點：這些是「內部模型」的值域，不是公司 JSON 的值域。
公司端 JSON 若使用不同的分類字串（例如中文、或不同英文代碼），
一律在 Adapter 層轉換成這裡的常數，UI 永遠只認得這裡的值。
"""


class MailCategory:
    """郵件分類（AI 判定）。"""

    ACTION_REQUIRED = "Action Required"   # 需要本人處理
    ALERT = "Alert"                       # 系統 / 設備告警
    IMPORTANT = "Important"               # 重要但不一定要動作
    MEETING = "Meeting"                   # 會議邀請
    PROJECT = "Project"                   # 專案進度
    REPORT = "Report"                     # 報表 / Daily Report
    INFO = "Info"                         # 一般資訊
    AUTO = "Auto Notification"            # 自動系統通知
    JUNK = "Junk"                         # 廣告 / 垃圾郵件

    ALL = (
        ACTION_REQUIRED,
        ALERT,
        IMPORTANT,
        MEETING,
        PROJECT,
        REPORT,
        INFO,
        AUTO,
        JUNK,
    )

    LABELS = {
        ACTION_REQUIRED: "需要處理",
        ALERT: "系統告警",
        IMPORTANT: "重要郵件",
        MEETING: "會議邀請",
        PROJECT: "專案進度",
        REPORT: "報表",
        INFO: "一般資訊",
        AUTO: "自動通知",
        JUNK: "垃圾郵件",
    }

    @classmethod
    def label(cls, category: str) -> str:
        """取得分類的中文顯示名稱。"""
        return cls.LABELS.get(category, category or "未分類")


class BlockType:
    """郵件內容區塊型別（對應 Lotus Notes 擷取後的多模態格式）。"""

    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    LIST = "list"
    QUOTE = "quote"


class Severity:
    """系統 / 設備事件嚴重度。"""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    RESOLVED = "resolved"

    LABELS = {
        CRITICAL: "嚴重",
        WARNING: "警告",
        INFO: "資訊",
        RESOLVED: "已解決",
    }

    @classmethod
    def label(cls, severity: str) -> str:
        """取得嚴重度的中文顯示名稱。"""
        return cls.LABELS.get(severity, severity)


class MailFilter:
    """Mail List 上方的 Filter 值。"""

    ALL = "all"
    IMPORTANT = "important"
    ACTION = "action"
    ALERT = "alert"
    REPORT = "report"

    ORDER = (ALL, IMPORTANT, ACTION, ALERT, REPORT)

    LABELS = {
        ALL: "全部",
        IMPORTANT: "重要",
        ACTION: "需處理",
        ALERT: "告警",
        REPORT: "報表",
    }


class NavKey:
    """Sidebar 導覽項目的識別碼。

    Sidebar 只送出這個 key，實際「這個 key 代表哪些郵件」由 MailService 決定。
    """

    TODAY = "today"

    INBOX_ACTION = "inbox_action"
    INBOX_IMPORTANT = "inbox_important"
    INBOX_TODO = "inbox_todo"
    INBOX_ALERT = "inbox_alert"
    INBOX_KEYPERSON = "inbox_keyperson"
    INBOX_REPORT = "inbox_report"
    INBOX_INFO = "inbox_info"
    INBOX_AUTO = "inbox_auto"

    TIME_YESTERDAY = "time_yesterday"
    TIME_WEEK = "time_week"
    TIME_HISTORY = "time_history"

    ASK_AI = "ask_ai"
    SETTINGS = "settings"
