"""Original Mail Viewer（三欄工作區中欄，45%）。

**這個元件只顯示原始郵件內容，絕對不顯示任何 AI 產生的文字。**
AI 相關內容一律放在右欄的 AI Analysis Panel，兩者以標題與配色明確區隔。

content_blocks 依原始順序渲染（文字 → 圖片 → 文字 → 表格 …），
對應未來 Lotus Notes 擷取後的多模態郵件格式。
"""

from __future__ import annotations

import reflex as rx

from ..models import Attachment, ContentBlock
from ..states import AppState
from ..theme import C, S
from .ui import empty_state, panel

#: 附件圖示種類 → lucide icon。
_ICONS = {
    "pdf": "file-text",
    "sheet": "file-spreadsheet",
    "doc": "file-type",
    "slides": "presentation",
    "image": "file-image",
    "archive": "file-archive",
    "file": "file",
}


# --------------------------------------------------------------------------
# 內容區塊
# --------------------------------------------------------------------------
def _text_block(block: ContentBlock) -> rx.Component:
    return rx.text(
        block.text,
        size="2",
        color=C.TEXT,
        line_height="1.85",
        white_space="pre-wrap",
        width="100%",
    )


def _quote_block(block: ContentBlock) -> rx.Component:
    return rx.box(
        rx.text(
            block.text,
            size="2",
            color=C.TEXT_SECONDARY,
            line_height="1.75",
            white_space="pre-wrap",
        ),
        width="100%",
        padding="10px 14px",
        background=C.SURFACE_ALT,
        border_left=f"3px solid {C.BORDER_STRONG}",
        border_radius=S.RADIUS_SM,
    )


def _image_block(block: ContentBlock) -> rx.Component:
    return rx.vstack(
        rx.image(
            src=block.src,
            width="100%",
            border=f"1px solid {C.BORDER}",
            border_radius=S.RADIUS_SM,
            background=C.SURFACE,
        ),
        rx.cond(
            block.caption != "",
            rx.text(block.caption, size="1", color=C.TEXT_MUTED),
            rx.fragment(),
        ),
        spacing="2",
        align="center",
        width="100%",
    )


def _table_block(block: ContentBlock) -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.foreach(
                            block.columns,
                            lambda col: rx.table.column_header_cell(
                                rx.text(col, size="1", weight="bold"),
                                background=C.BG_SUBTLE,
                                white_space="nowrap",
                            ),
                        ),
                    ),
                ),
                rx.table.body(
                    rx.foreach(
                        block.rows,
                        lambda row: rx.table.row(
                            rx.foreach(
                                row,
                                lambda cell: rx.table.cell(
                                    rx.text(cell, size="1"),
                                    white_space="nowrap",
                                ),
                            ),
                        ),
                    ),
                ),
                variant="surface",
                size="1",
                width="100%",
            ),
            width="100%",
            overflow_x="auto",
        ),
        rx.cond(
            block.caption != "",
            rx.text(block.caption, size="1", color=C.TEXT_MUTED),
            rx.fragment(),
        ),
        spacing="2",
        align="center",
        width="100%",
    )


def _list_block(block: ContentBlock) -> rx.Component:
    return rx.vstack(
        rx.foreach(
            block.list_items,
            lambda item: rx.hstack(
                rx.box(
                    width="5px",
                    height="5px",
                    border_radius=S.RADIUS_PILL,
                    background=C.TEXT_MUTED,
                    margin_top="9px",
                    flex_shrink="0",
                ),
                rx.text(item, size="2", color=C.TEXT, line_height="1.8"),
                spacing="2",
                align="start",
                width="100%",
            ),
        ),
        spacing="0",
        width="100%",
        padding_left="6px",
    )


def _content_block(block: ContentBlock) -> rx.Component:
    """依 block_type 分流渲染，維持原始閱讀順序。"""
    return rx.match(
        block.block_type,
        ("text", _text_block(block)),
        ("image", _image_block(block)),
        ("table", _table_block(block)),
        ("list", _list_block(block)),
        ("quote", _quote_block(block)),
        _text_block(block),
    )


# --------------------------------------------------------------------------
# 表頭與附件
# --------------------------------------------------------------------------
def _meta_row(label: str, value: rx.Var) -> rx.Component:
    return rx.hstack(
        rx.text(label, size="1", color=C.TEXT_MUTED, width="34px", flex_shrink="0"),
        rx.text(value, size="1", color=C.TEXT_SECONDARY, line_height="1.5"),
        spacing="2",
        align="start",
        width="100%",
    )


def _mail_header() -> rx.Component:
    mail = AppState.selected_mail
    return rx.vstack(
        rx.hstack(
            rx.text("原始郵件", size="1", color=C.TEXT_MUTED, weight="medium"),
            rx.text("Lotus Notes 原文，未經 AI 加工", size="1", color=C.TEXT_MUTED),
            rx.spacer(),
            rx.text(mail.source, size="1", color=C.TEXT_MUTED),
            spacing="2",
            align="center",
            width="100%",
        ),
        rx.text(
            mail.subject,
            size="4",
            weight="bold",
            color=C.TEXT,
            line_height="1.45",
        ),
        rx.hstack(
            rx.center(
                rx.text(
                    mail.sender.initials,
                    size="2",
                    weight="bold",
                    color=C.TEXT_INVERSE,
                ),
                background=rx.cond(mail.sender.is_key_person, C.PRIMARY, C.TEXT_MUTED),
                border_radius=S.RADIUS_PILL,
                width="36px",
                height="36px",
                flex_shrink="0",
            ),
            rx.vstack(
                rx.hstack(
                    rx.text(
                        mail.sender.name,
                        size="2",
                        weight="bold",
                        color=C.TEXT,
                    ),
                    rx.text(
                        mail.sender.title,
                        size="1",
                        color=C.TEXT_MUTED,
                    ),
                    rx.text(
                        "<" + mail.sender.email + ">",
                        size="1",
                        color=C.TEXT_MUTED,
                    ),
                    spacing="2",
                    align="center",
                ),
                _meta_row("To", mail.to_label),
                _meta_row("Cc", mail.cc_label),
                spacing="1",
                align="start",
                flex="1",
                min_width="0",
            ),
            rx.text(
                mail.datetime_label,
                size="1",
                color=C.TEXT_MUTED,
                flex_shrink="0",
            ),
            spacing="3",
            align="start",
            width="100%",
        ),
        spacing="3",
        width="100%",
        align="start",
        padding="14px 16px",
        border_bottom=f"1px solid {C.BORDER}",
        background=C.SURFACE,
        flex_shrink="0",
    )


def _attachment(item: Attachment) -> rx.Component:
    """附件項目。

    Mock 階段沒有實體檔案，downloadable=False 時顯示為停用狀態。
    這是資料屬性，元件不需要知道目前是不是 Mock 模式。
    """
    return rx.hstack(
        # rx.icon 的 tag 必須是編譯期常數（要據此決定 import 哪個 lucide 圖示），
        # 因此改成「先建好每種圖示的元件，再用 rx.match 挑一個」。
        rx.match(
            item.icon_key,
            *[
                (key, rx.icon(tag, size=16, color=C.TEXT_SECONDARY, flex_shrink="0"))
                for key, tag in _ICONS.items()
            ],
            rx.icon("file", size=16, color=C.TEXT_SECONDARY, flex_shrink="0"),
        ),
        rx.vstack(
            rx.text(
                item.filename,
                size="1",
                color=C.TEXT,
                weight="medium",
                line_height="1.3",
            ),
            rx.text(item.size_label, size="1", color=C.TEXT_MUTED, line_height="1.3"),
            spacing="0",
            align="start",
        ),
        rx.icon(
            "download",
            size=14,
            color=rx.cond(item.downloadable, C.PRIMARY, C.TEXT_MUTED),
        ),
        spacing="2",
        align="center",
        padding="7px 10px",
        background=C.SURFACE,
        border=f"1px solid {C.BORDER}",
        border_radius=S.RADIUS_SM,
        opacity=rx.cond(item.downloadable, "1", "0.65"),
        cursor=rx.cond(item.downloadable, "pointer", "not-allowed"),
        title=rx.cond(
            item.downloadable, "下載附件", "Mock 階段沒有實體檔案，無法下載"
        ),
    )


def _attachments() -> rx.Component:
    mail = AppState.selected_mail
    return rx.cond(
        mail.attachment_count > 0,
        rx.vstack(
            rx.hstack(
                rx.icon("paperclip", size=14, color=C.TEXT_SECONDARY),
                rx.text(
                    f"附件（{mail.attachment_count}）",
                    size="1",
                    weight="bold",
                    color=C.TEXT_SECONDARY,
                ),
                spacing="2",
                align="center",
            ),
            rx.flex(
                rx.foreach(mail.attachments, _attachment),
                wrap="wrap",
                gap="8px",
                width="100%",
            ),
            spacing="2",
            align="start",
            width="100%",
            padding="12px 16px",
            border_top=f"1px solid {C.BORDER}",
            background=C.SURFACE_ALT,
            flex_shrink="0",
        ),
        rx.fragment(),
    )


# --------------------------------------------------------------------------
# 主體
# --------------------------------------------------------------------------
def mail_viewer() -> rx.Component:
    """中欄：原始郵件。"""
    return panel(
        rx.cond(
            AppState.has_selection,
            rx.fragment(
                _mail_header(),
                rx.box(
                    rx.vstack(
                        rx.foreach(
                            AppState.selected_mail.content_blocks, _content_block
                        ),
                        spacing="4",
                        width="100%",
                        align="start",
                        padding="18px 16px",
                    ),
                    flex="1",
                    overflow_y="auto",
                    min_height="0",
                    background=C.SURFACE,
                ),
                _attachments(),
            ),
            empty_state(
                "請從左側選擇一封郵件",
                "選取後這裡會顯示未經加工的原始郵件內容",
                icon="mail-open",
                height="100%",
            ),
        ),
        flex="1",
        min_width="0",
        height="100%",
    )
