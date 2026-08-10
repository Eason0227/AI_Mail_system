"""Dashboard 相關模型。"""

import dataclasses
from typing import List

from .mail import Mail


@dataclasses.dataclass
class KpiSummary:
    """首頁最上方的 KPI 數字。

    這些數字一律由 Service 依實際資料計算，不在 UI 寫死。
    """

    total_today: int = 0        # 今日郵件
    important: int = 0          # 重要郵件
    todo: int = 0               # 待辦事項
    system_events: int = 0      # 系統 / 設備事件
    general_info: int = 0       # 一般資訊

    unread_today: int = 0       # 今日未讀（副標顯示用）
    overdue: int = 0            # 已逾期待辦
    due_soon: int = 0           # 3 天內到期
    resolved_alerts: int = 0    # 已解決事件


@dataclasses.dataclass
class BriefHighlight:
    """AI 今日重點的單一條目。"""

    index: int = 0
    text: str = ""
    severity: str = "info"      # critical / warning / info
    mail_id: str = ""           # 可點擊跳轉的來源郵件


@dataclasses.dataclass
class DailyBrief:
    """AI 今日重點摘要。"""

    generated_at_label: str = ""
    headline: str = ""                  # "今天主要有三件需要關注："
    highlights: List[BriefHighlight] = dataclasses.field(default_factory=list)
    full_text: str = ""                 # 「查看完整 Daily Brief」的內容
    model_name: str = ""


@dataclasses.dataclass
class SystemAlert:
    """系統 / 設備事件。"""

    alert_id: str = ""
    equipment: str = ""          # "B1_SCOP_03"
    alert_type: str = ""         # "Particle OOB"
    description: str = ""

    metric_label: str = ""       # "OOB Rate"
    metric_value: str = ""       # "18.7%"
    duration_label: str = ""     # "3 Days"

    severity: str = "warning"    # models.enums.Severity
    severity_label: str = "警告"
    status: str = "open"         # open / monitoring / resolved
    status_label: str = "處理中"

    occurred_at: str = ""        # ISO
    occurred_at_label: str = ""  # "2026/08/07 08:10"
    related_mail_id: str = ""
    owner: str = ""              # 負責單位

    # 同一類告警在期間內出現幾次。
    # 公司端會用 alert_key 把重複的固定格式告警聚合（52 封 -> 31 組），
    # UI 顯示代表事件並標註次數，避免一頁塞滿同樣的告警。
    occurrence_count: int = 1


@dataclasses.dataclass
class DashboardSummary:
    """Dashboard 首頁一次取得的完整資料。

    UI 只呼叫 dashboard_service.get_dashboard_summary() 一次就拿到全部，
    不需要自己組合多個來源。
    """

    kpi: KpiSummary = dataclasses.field(default_factory=KpiSummary)
    brief: DailyBrief = dataclasses.field(default_factory=DailyBrief)
    action_mails: List[Mail] = dataclasses.field(default_factory=list)
    alerts: List[SystemAlert] = dataclasses.field(default_factory=list)
    today_label: str = ""
    last_update_label: str = ""
