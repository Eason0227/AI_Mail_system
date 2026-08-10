"""附件模型。"""

import dataclasses

_IMAGE_EXT = ("png", "jpg", "jpeg", "gif", "bmp", "svg", "webp")
_SHEET_EXT = ("xlsx", "xls", "csv")
_DOC_EXT = ("doc", "docx")
_SLIDE_EXT = ("ppt", "pptx")
_ARCHIVE_EXT = ("zip", "rar", "7z")


def resolve_icon_key(file_type: str) -> str:
    """由副檔名決定要顯示的圖示種類。"""
    t = (file_type or "").lower().lstrip(".")
    if t in _IMAGE_EXT:
        return "image"
    if t in _SHEET_EXT:
        return "sheet"
    if t == "pdf":
        return "pdf"
    if t in _DOC_EXT:
        return "doc"
    if t in _SLIDE_EXT:
        return "slides"
    if t in _ARCHIVE_EXT:
        return "archive"
    return "file"


@dataclasses.dataclass
class Attachment:
    """郵件附件。

    url 是「已經可以直接使用的位址」。
    Mock 階段指向 assets/ 下的靜態檔；公司環境可由 Adapter 換成
    Python 服務提供的下載端點，UI 不需要知道差別。

    注意：icon_key 是實體欄位而非 property，因為 Reflex 的 Var
    只能存取 dataclass 的真實欄位。一律由 Adapter 呼叫
    resolve_icon_key() 後填入。
    """

    attachment_id: str = ""
    filename: str = ""
    file_type: str = ""        # pdf / xlsx / docx / png / csv ...
    size_label: str = ""       # 已格式化的大小，例如 "1.4 MB"
    url: str = ""              # 下載 / 預覽位址
    is_inline: bool = False    # 是否為內文嵌入圖片（不列在附件清單）
    icon_key: str = "file"     # 顯示用圖示種類，由 resolve_icon_key() 產生

    # 是否真的可以下載。Mock 階段沒有實體檔案 -> False，UI 顯示為停用狀態。
    # 公司環境接上實際附件後由 Adapter 設為 True。
    # 用資料屬性表達，UI 就不需要知道目前是不是 Mock 模式。
    downloadable: bool = False
