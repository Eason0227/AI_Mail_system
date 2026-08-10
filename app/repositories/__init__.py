"""資料存取層。

**整個系統唯一決定「資料從哪裡來」的地方。**

上層（Service / State / UI）一律透過 ``get_mail_repository()`` 取得實例，
永遠不直接 import MockMailRepository 或 RealMailRepository，
因此把 config.DATA_MODE 從 "mock" 改成 "real" 就完成資料來源切換。
"""

from __future__ import annotations

from typing import Optional

from .. import config
from .base_mail_repository import BaseMailRepository

_instance: Optional[BaseMailRepository] = None


def create_mail_repository(mode: Optional[str] = None) -> BaseMailRepository:
    """依 DATA_MODE 建立 Repository 實例。

    Args:
        mode: 覆寫 config.DATA_MODE，測試用。
    """
    data_mode = (mode or config.DATA_MODE).strip().lower()

    if data_mode == "real":
        # 延後 import：Mock 模式下不需要載入公司端相關模組。
        from .real_mail_repository import RealMailRepository

        return RealMailRepository()

    from .mock_mail_repository import MockMailRepository

    return MockMailRepository()


def get_mail_repository() -> BaseMailRepository:
    """取得 Repository 單例。"""
    global _instance
    if _instance is None:
        _instance = create_mail_repository()
    return _instance


def reset_mail_repository() -> None:
    """丟棄單例，下次取用時重新建立（設定頁「重新載入資料來源」使用）。"""
    global _instance
    _instance = None


__all__ = [
    "BaseMailRepository",
    "create_mail_repository",
    "get_mail_repository",
    "reset_mail_repository",
]
