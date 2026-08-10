"""AI 結構化分析結果模型。

這是 UI 唯一認得的 AI 分析格式。
未來 Multimodal LLM 輸出的公司 JSON 不論長什麼樣，
都必須由 Adapter 轉成這裡的結構。

設計注意事項
------------
所有 UI 需要顯示的衍生值（星號字串、逾期旗標、顯示用日期…）
一律做成「實體欄位」，由 Adapter 在建立物件時一次算好。
不要用 @property，因為 Reflex 的 Var 無法存取 property。
"""

import dataclasses
from typing import List


@dataclasses.dataclass
class TodoItem:
    """AI 拆解出的待辦事項。"""

    todo_id: str = ""
    text: str = ""
    done: bool = False
    deadline_label: str = ""  # 顯示用，例如 "2026/08/14"，無則空字串
    priority: str = "normal"  # high / normal / low
    mail_id: str = ""         # 來源郵件
    mail_subject: str = ""    # 來源郵件主旨（待辦頁面顯示用）


@dataclasses.dataclass
class KeyFact:
    """AI 抽取出的關鍵資訊（欄位 / 數值成對）。"""

    label: str = ""
    value: str = ""
    emphasis: bool = False    # 是否要以強調色顯示（例如超出規格的數值）


@dataclasses.dataclass
class AIAnalysis:
    """單封郵件的 AI 分析結果。"""

    mail_id: str = ""

    # ---- 判定 ----
    importance: int = 0                 # 1~5
    category: str = "Info"              # models.enums.MailCategory
    category_label: str = "一般資訊"     # 中文顯示名稱
    action_required: bool = False

    # ---- Deadline ----
    deadline: str = ""                  # ISO 日期字串（YYYY-MM-DD），無則空字串
    deadline_label: str = ""            # 顯示用，例如 "2026/08/14"
    deadline_days_left: int = 999       # 距今天數；無 deadline 時為 999
    has_deadline: bool = False
    is_overdue: bool = False
    is_due_soon: bool = False           # 3 天內到期

    # ---- 內容 ----
    summary: str = ""
    todos: List[TodoItem] = dataclasses.field(default_factory=list)
    recommendations: List[str] = dataclasses.field(default_factory=list)
    key_facts: List[KeyFact] = dataclasses.field(default_factory=list)
    reply_draft: str = ""

    # 純文字重點條列。
    # 公司端 LLM 輸出的 key_points 是字串陣列，沒有 label/value 配對，
    # 硬塞進 key_facts 會產生一堆空標籤，因此另開一個欄位承接。
    # UI 規則：key_facts 有值就顯示表格，否則顯示 key_points 條列。
    key_points: List[str] = dataclasses.field(default_factory=list)

    # ---- 收件人關係（公司端 LLM 的 addressed_to_me）----
    # direct（本人為直接收件人）/ cc（僅副本）/ broadcast（群發）/ ""（未判定）
    addressed_to: str = ""
    addressed_to_label: str = ""

    # ---- 顯示用衍生值 ----
    importance_stars: str = "☆☆☆☆☆"
    has_analysis: bool = False

    # ---- 追溯資訊 ----
    model_name: str = ""
    analyzed_at: str = ""
    confidence: float = 0.0
    confidence_label: str = ""   # 顯示用，例如 "92%"；無分析結果時為空字串


def build_importance_stars(importance: int) -> str:
    """把 1~5 的重要度轉成星號字串。"""
    n = max(0, min(5, int(importance or 0)))
    return "★" * n + "☆" * (5 - n)
