"""告警主旨解析器。

為什麼需要這個
--------------
公司端 Step A 對 machine_alert 類郵件抓不到本文（64 封裡有 49 封 blocks 為空，
且全部都是 machine_alert）。但這類告警是固定格式的系統信，
**所有資訊本來就在主旨裡**，因此不需要回頭修 Step A，
在這裡把主旨拆開就能填滿 SystemAlert 模型。

支援的主旨格式（以下機台代號為示意值，實際代號依廠區而定）::

    【汙染因子超標通知】<區域> 關鍵機台 <機台> - PSN <點位> 狀態 OOS
    【汙染因子超標通知】<區域> 非關鍵機台 <機台> - PSN <點位> 狀態 OOS
    【汙染因子超標通知】<區域> <機台> - PSN <點位> 狀態 OOS
    【PSN裝置斷線通知】<區域> 共 N 台
    [ <系統名>系統通知 ] 裝置服務離線警報 - N 個模組離線

主旨結尾可能帶公司的資料分級標記，顯示前由 strip_security_tag() 移除。

解析不出來時一律回傳空值，不拋例外——單一主旨變形不應該讓整個 Dashboard 掛掉。
"""

from __future__ import annotations

import dataclasses
import re
from typing import Optional

#: 公司資料分級標記，顯示前先移除。
_SECURITY_TAG = re.compile(r"\s*[（(]\s*Security\s+\w+\s*[)）]\s*$", re.IGNORECASE)

#: 【汙染因子超標通知】<區域> [關鍵性] <機台> - PSN <點位> 狀態 <狀態>
_OOS = re.compile(
    r"【汙染因子超標通知】\s*"
    r"(?P<area>\S+)\s+"
    r"(?:(?P<criticality>關鍵機台|非關鍵機台)\s+)?"
    r"(?P<equipment>\S+)\s*-\s*"
    r"PSN\s+(?P<psn>\S+)\s*"
    r"狀態\s*(?P<status>\S+)"
)

#: 【PSN裝置斷線通知】<區域> 共<N>台
_OFFLINE = re.compile(r"【PSN裝置斷線通知】\s*(?P<area>.+?)\s*共\s*(?P<count>\d+)\s*台")

#: [ WB-PHM系統通知 ] 裝置服務離線警報 - <N> 個模組離線
_MODULE_OFFLINE = re.compile(
    r"\[\s*(?P<system>[\w\-]+)系統通知\s*\].*?(?P<count>\d+)\s*個模組離線"
)


@dataclasses.dataclass
class ParsedAlert:
    """從主旨解析出來的告警內容。

    欄位對應 models.SystemAlert，解析不到的一律留空字串。
    """

    equipment: str = ""        # 機台代號
    area: str = ""             # 廠區 / 線別
    metric_label: str = ""     # 指標名稱，例如 "PSN 點位" / "離線台數"
    metric_value: str = ""     # 指標值，例如 "5 台"
    status_text: str = ""      # 狀態，例如 "OOS"
    is_critical: bool = False  # 是否為關鍵機台
    matched: bool = False      # 是否成功解析


def strip_security_tag(text: str) -> str:
    """移除主旨結尾的 "(Security C)" 這類公司資料分級標記。"""
    return _SECURITY_TAG.sub("", text or "").strip()


def parse_alert_subject(subject: str) -> ParsedAlert:
    """解析告警主旨。

    Args:
        subject: 原始主旨（可含 Security 標記）。

    Returns:
        ParsedAlert；無法辨識時 matched=False。
    """
    text = strip_security_tag(subject)
    if not text:
        return ParsedAlert()

    m = _OOS.search(text)
    if m:
        return ParsedAlert(
            equipment=m.group("equipment"),
            area=m.group("area"),
            metric_label="PSN 點位",
            metric_value=m.group("psn"),
            status_text=m.group("status"),
            is_critical=(m.group("criticality") == "關鍵機台"),
            matched=True,
        )

    m = _OFFLINE.search(text)
    if m:
        area = m.group("area")
        return ParsedAlert(
            equipment=area,
            area=area,
            metric_label="離線台數",
            metric_value=f"{m.group('count')} 台",
            status_text="斷線",
            matched=True,
        )

    m = _MODULE_OFFLINE.search(text)
    if m:
        system = m.group("system")
        return ParsedAlert(
            equipment=system,
            area=system,
            metric_label="離線模組",
            metric_value=f"{m.group('count')} 個",
            status_text="離線",
            matched=True,
        )

    return ParsedAlert()


def resolve_equipment(machine: Optional[str], subject: str) -> str:
    """決定要顯示的機台代號。

    公司 summary 的 machine 欄位在部分告警是 "N/A"，此時退回主旨解析。
    """
    value = (machine or "").strip()
    if value and value.upper() != "N/A":
        return value
    return parse_alert_subject(subject).equipment
