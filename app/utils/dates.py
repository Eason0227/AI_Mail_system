"""日期時間格式化工具。

集中放這裡的原因：UI 不做資料加工，所有顯示用字串都在 Adapter 產生。
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

WEEKDAY_ZH = ("一", "二", "三", "四", "五", "六", "日")


def parse_iso(value: str) -> Optional[datetime]:
    """寬鬆解析 ISO 8601 字串，失敗回傳 None。"""
    if not value:
        return None
    text = str(value).strip().replace("Z", "").replace("/", "-")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def parse_iso_date(value: str) -> Optional[date]:
    """解析成日期（只取日期部分）。"""
    dt = parse_iso(value)
    return dt.date() if dt else None


def fmt_time(dt: datetime) -> str:
    """"10:24"。"""
    return dt.strftime("%H:%M")


def fmt_date(dt: datetime | date) -> str:
    """"2026/08/09"。"""
    return dt.strftime("%Y/%m/%d")


def fmt_month_day(dt: datetime | date) -> str:
    """"08/09"。"""
    return dt.strftime("%m/%d")


def fmt_weekday(dt: datetime | date) -> str:
    """"五"。"""
    return WEEKDAY_ZH[dt.weekday()]


def fmt_datetime_label(dt: datetime) -> str:
    """"2026/08/09 (五) 10:24"。"""
    return f"{fmt_date(dt)} ({fmt_weekday(dt)}) {fmt_time(dt)}"


def fmt_day_label(dt: datetime, today: date) -> str:
    """"今天" / "昨天" / "2026/08/07"。"""
    delta = (today - dt.date()).days
    if delta == 0:
        return "今天"
    if delta == 1:
        return "昨天"
    if delta == -1:
        return "明天"
    return fmt_date(dt)


def fmt_list_time_label(dt: datetime, today: date) -> str:
    """Mail List 用的緊湊時間：今天顯示時間，昨天顯示「昨天」，更早顯示日期。"""
    delta = (today - dt.date()).days
    if delta == 0:
        return fmt_time(dt)
    if delta == 1:
        return "昨天"
    if 0 < delta < 7:
        return f"週{fmt_weekday(dt)}"
    return fmt_month_day(dt)


def days_until(target: date, today: date) -> int:
    """距離目標日期還有幾天（負數代表已逾期）。"""
    return (target - today).days


def start_of_week(today: date) -> date:
    """本週一。"""
    return today - timedelta(days=today.weekday())


def fmt_today_header(today: date) -> str:
    """Header 用："2026/08/09 (日)"。"""
    return f"{fmt_date(today)} ({fmt_weekday(today)})"
