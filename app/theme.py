"""視覺設計 Token。

所有顏色、圓角、陰影、字級集中在這裡，Component 不要自己寫死色碼。
風格：Enterprise SaaS / Clean / Professional / Card-based。
"""

from __future__ import annotations


# --------------------------------------------------------------------------
# 色彩
# --------------------------------------------------------------------------
class C:
    """Color tokens."""

    # 背景
    BG = "#F4F6F8"          # 頁面底色（淺灰）
    BG_SUBTLE = "#EDF0F4"   # 次級底色
    SURFACE = "#FFFFFF"     # 卡片 / 面板
    SURFACE_ALT = "#FAFBFC"  # 卡片內次級區塊
    SIDEBAR_BG = "#FFFFFF"
    HEADER_BG = "#FFFFFF"

    # 線條
    BORDER = "#E3E8EF"
    BORDER_STRONG = "#CDD5E0"

    # 文字
    TEXT = "#1B2434"        # 主要文字
    TEXT_SECONDARY = "#5A6B85"
    TEXT_MUTED = "#8B99AE"
    TEXT_INVERSE = "#FFFFFF"

    # 主色（藍色 Accent）
    PRIMARY = "#2563EB"
    PRIMARY_HOVER = "#1D4ED8"
    PRIMARY_SOFT = "#EFF4FF"
    PRIMARY_BORDER = "#BFD3FE"

    # 語意色
    DANGER = "#DC2626"       # 紅 = 緊急
    DANGER_SOFT = "#FEF0F0"
    DANGER_BORDER = "#F7C9C9"

    WARNING = "#EA8A0B"      # 橘 = Warning
    WARNING_SOFT = "#FFF6E9"
    WARNING_BORDER = "#F8DCB0"

    SUCCESS = "#12945F"      # 綠 = Completed
    SUCCESS_SOFT = "#EAF7F1"
    SUCCESS_BORDER = "#B7E2CE"

    INFO = "#5A6B85"         # 灰藍 = 一般資訊
    INFO_SOFT = "#F1F4F8"
    INFO_BORDER = "#DCE3EC"

    PURPLE = "#7C4DEB"       # AI 專用強調色
    PURPLE_SOFT = "#F4F0FE"
    PURPLE_BORDER = "#DCCFFB"

    STAR = "#F5A524"         # 重要度星號


# --------------------------------------------------------------------------
# 尺寸
# --------------------------------------------------------------------------
class S:
    """Size / spacing tokens."""

    HEADER_H = "60px"
    SIDEBAR_W = "236px"
    ASKAI_H = "68px"

    RADIUS_SM = "6px"
    RADIUS = "10px"       # 卡片主要圓角（8~12px）
    RADIUS_LG = "12px"
    RADIUS_PILL = "999px"

    SHADOW = "0 1px 2px rgba(16,24,40,0.04), 0 1px 3px rgba(16,24,40,0.06)"
    SHADOW_HOVER = "0 4px 10px rgba(16,24,40,0.08), 0 2px 4px rgba(16,24,40,0.06)"
    SHADOW_HEADER = "0 1px 3px rgba(16,24,40,0.06)"

    # 主內容區與底部 Ask AI 之間留白
    PAGE_PAD = "20px"


# --------------------------------------------------------------------------
# 分類 / 嚴重度 → 顏色對應
# --------------------------------------------------------------------------
# key 使用 models.enums 的常數字串
CATEGORY_COLORS: dict[str, tuple[str, str, str]] = {
    # category: (文字色, 底色, 邊框色)
    "Action Required": (C.DANGER, C.DANGER_SOFT, C.DANGER_BORDER),
    "Alert": (C.WARNING, C.WARNING_SOFT, C.WARNING_BORDER),
    "Important": (C.PRIMARY, C.PRIMARY_SOFT, C.PRIMARY_BORDER),
    "Meeting": (C.PURPLE, C.PURPLE_SOFT, C.PURPLE_BORDER),
    "Project": (C.PRIMARY, C.PRIMARY_SOFT, C.PRIMARY_BORDER),
    "Report": (C.SUCCESS, C.SUCCESS_SOFT, C.SUCCESS_BORDER),
    "Info": (C.INFO, C.INFO_SOFT, C.INFO_BORDER),
    "Auto Notification": (C.TEXT_MUTED, C.INFO_SOFT, C.INFO_BORDER),
    "Junk": (C.TEXT_MUTED, C.BG_SUBTLE, C.BORDER),
}

SEVERITY_COLORS: dict[str, tuple[str, str, str]] = {
    "critical": (C.DANGER, C.DANGER_SOFT, C.DANGER_BORDER),
    "warning": (C.WARNING, C.WARNING_SOFT, C.WARNING_BORDER),
    "info": (C.INFO, C.INFO_SOFT, C.INFO_BORDER),
    "resolved": (C.SUCCESS, C.SUCCESS_SOFT, C.SUCCESS_BORDER),
}


def category_color(category: str) -> tuple[str, str, str]:
    """取得分類對應的 (文字色, 底色, 邊框色)。"""
    return CATEGORY_COLORS.get(category, CATEGORY_COLORS["Info"])


def severity_color(severity: str) -> tuple[str, str, str]:
    """取得嚴重度對應的 (文字色, 底色, 邊框色)。"""
    return SEVERITY_COLORS.get(severity, SEVERITY_COLORS["info"])
