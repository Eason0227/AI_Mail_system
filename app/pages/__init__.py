"""頁面層。"""

from .alerts import alerts_page
from .ask_ai import ask_ai_page
from .dashboard import dashboard_page
from .mail import mail_page, mail_workspace
from .reports import reports_page
from .settings import settings_page
from .todo import todo_page

__all__ = [
    "alerts_page",
    "ask_ai_page",
    "dashboard_page",
    "mail_page",
    "mail_workspace",
    "reports_page",
    "settings_page",
    "todo_page",
]
