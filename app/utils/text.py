"""文字處理工具。"""

from __future__ import annotations

from typing import List


def truncate(text: str, limit: int) -> str:
    """截斷字串並補上省略號。"""
    clean = " ".join((text or "").split())
    if len(clean) <= limit:
        return clean
    return clean[:limit].rstrip() + "…"


def fmt_size(size_bytes: int) -> str:
    """位元組數轉成可讀字串，例如 "1.4 MB"。"""
    try:
        size = float(size_bytes or 0)
    except (TypeError, ValueError):
        return ""
    if size <= 0:
        return ""
    for unit, digits in (("B", 0), ("KB", 0), ("MB", 1), ("GB", 2)):
        if size < 1024 or unit == "GB":
            return f"{size:.{digits}f} {unit}"
        size /= 1024
    return ""


def initials_of(name: str) -> str:
    """取名字的頭像文字。

    中文取姓（第一個字），英文取首字母。
    """
    clean = (name or "").strip()
    if not clean:
        return "?"
    first = clean[0]
    if first.isascii() and first.isalpha():
        return first.upper()
    return first


def join_recipients(recipients: List[str], max_shown: int = 2) -> str:
    """收件者清單轉顯示字串。"""
    items = [r for r in (recipients or []) if r]
    if not items:
        return "—"
    if len(items) <= max_shown:
        return "、".join(items)
    shown = "、".join(items[:max_shown])
    return f"{shown} 等 {len(items)} 人"
