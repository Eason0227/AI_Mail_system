"""郵件模型。

這是 UI 唯一認得的郵件格式。Lotus Notes / 公司 JSON 的原始欄位
一律由 Adapter 轉換成這裡的結構。

設計注意事項
------------
1. 所有 UI 需要顯示的字串（時間標籤、收件者字串、預覽文字…）
   都是實體欄位，由 Adapter 一次算好，Component 不做資料加工。
2. content_blocks 保留郵件原始閱讀順序，Mail Viewer 依序渲染。
"""

import dataclasses
from typing import List

from .ai_analysis import AIAnalysis
from .attachment import Attachment


@dataclasses.dataclass
class Sender:
    """寄件者。"""

    name: str = ""
    email: str = ""
    initials: str = ""          # 頭像文字，例如 "王"
    is_key_person: bool = False  # 是否為主管 / 關鍵窗口
    title: str = ""             # 職稱，例如 "製造部經理"


@dataclasses.dataclass
class ContentBlock:
    """郵件內容區塊。

    對應未來 Lotus Notes 擷取後的多模態郵件格式。
    以單一 dataclass 承載所有型別，UI 端用 block_type 分流渲染，
    避免 Reflex 需要處理 Union 型別。

    block_type:
        text   -> 使用 text
        image  -> 使用 src / caption
        table  -> 使用 columns / rows / caption
        list   -> 使用 list_items
        quote  -> 使用 text（引用原信段落）

    命名注意
    --------
    欄位不可取名為 items / to / keys / values 等 Reflex Var 的既有方法名，
    否則在 UI 端 ``block.items`` 會取到 ObjectVar.items() 這個方法而不是欄位。
    因此清單內容命名為 list_items。
    """

    block_type: str = "text"
    text: str = ""
    src: str = ""
    caption: str = ""
    columns: List[str] = dataclasses.field(default_factory=list)
    rows: List[List[str]] = dataclasses.field(default_factory=list)
    list_items: List[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Mail:
    """一封郵件。"""

    mail_id: str = ""
    subject: str = ""
    sender: Sender = dataclasses.field(default_factory=Sender)
    to: List[str] = dataclasses.field(default_factory=list)
    cc: List[str] = dataclasses.field(default_factory=list)

    # ---- 時間（全部為顯示就緒的字串）----
    sent_at: str = ""          # ISO 8601，例如 "2026-08-09T10:24:00"（排序/篩選用）
    time_label: str = ""       # "10:24"
    date_label: str = ""       # "2026/08/09"
    datetime_label: str = ""   # "2026/08/09 (五) 10:24"
    list_time_label: str = ""  # Mail List 用：今天->"10:24"，昨天->"昨天"，更早->"08/07"
    day_label: str = ""        # "今天" / "昨天" / "2026/08/07"

    # ---- 狀態 ----
    is_read: bool = False
    has_attachment: bool = False
    attachment_count: int = 0
    preview: str = ""          # 內文前段純文字預覽

    # ---- 收件者顯示字串 ----
    to_label: str = ""
    cc_label: str = ""

    # ---- 原始內容（保留閱讀順序）----
    content_blocks: List[ContentBlock] = dataclasses.field(default_factory=list)
    attachments: List[Attachment] = dataclasses.field(default_factory=list)

    # ---- AI 分析（與原始郵件內容明確分離）----
    ai: AIAnalysis = dataclasses.field(default_factory=AIAnalysis)

    # ---- 來源追溯 ----
    source: str = "Mock"       # "Mock" / "Lotus Notes"
    folder: str = "Inbox"


# 空郵件單例：State 尚未選取任何郵件時使用，避免 UI 需要處理 None。
EMPTY_MAIL = Mail()
