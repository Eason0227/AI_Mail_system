"""Ask AI 問答結果模型。"""

import dataclasses
from typing import List


@dataclasses.dataclass
class AskAIReference:
    """答案引用的來源郵件。"""

    mail_id: str = ""
    subject: str = ""
    sender_name: str = ""
    time_label: str = ""
    reason: str = ""          # 為什麼引用這封


@dataclasses.dataclass
class AskAIAnswer:
    """一次問答的結果。

    不論答案來自 Mock 規則比對或未來的 LLM，UI 拿到的都是這個結構。
    """

    question: str = ""
    answer: str = ""
    bullets: List[str] = dataclasses.field(default_factory=list)
    references: List[AskAIReference] = dataclasses.field(default_factory=list)
    engine: str = ""          # "mock-rule" / "llm:xxx"，顯示資料來源用
    answered_at_label: str = ""
    matched: bool = True      # 是否成功理解問題（Mock 階段可能無法回答）
