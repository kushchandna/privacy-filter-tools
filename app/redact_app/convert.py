from __future__ import annotations

import html
from pathlib import Path

NON_TEXT_EXTENSIONS = {
    "pdf",
    "docx",
    "doc",
    "pptx",
    "ppt",
    "xlsx",
    "xls",
    "odt",
    "ods",
    "odp",
}


def is_non_text_file(path: Path) -> bool:
    return path.suffix.lower().lstrip(".") in NON_TEXT_EXTENSIONS


def convert_to_markdown(input_path: Path) -> str:
    from docling.document_converter import DocumentConverter

    converter = DocumentConverter()
    conversion = converter.convert(str(input_path))
    markdown = conversion.document.export_to_markdown()
    return html.unescape(markdown)

