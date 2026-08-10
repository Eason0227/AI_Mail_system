"""State 層。

UI Component 只從這裡取得資料，不直接呼叫 Service，也不接觸 Repository。
"""

from .app_state import (
    TAB_RECOMMEND,
    TAB_REPLY,
    TAB_SUMMARY,
    TAB_TODO,
    AppState,
)

__all__ = [
    "TAB_RECOMMEND",
    "TAB_REPLY",
    "TAB_SUMMARY",
    "TAB_TODO",
    "AppState",
]
