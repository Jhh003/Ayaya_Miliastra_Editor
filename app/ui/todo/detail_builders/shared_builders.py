from __future__ import annotations

from typing import List

from app.models.todo_item import TodoItem
from app.ui.todo.todo_detail_model import (
    BulletListBlock,
    DetailDocument,
    DetailSection,
    ParagraphBlock,
    ParagraphStyle,
    TableBlock,
)


def build_simple_title_and_description_document(todo: TodoItem) -> DetailDocument:
    document = DetailDocument()
    section = DetailSection(title=str(todo.title), level=3)
    if todo.description:
        section.blocks.append(
            ParagraphBlock(
                text=str(todo.description),
                style=ParagraphStyle.NORMAL,
            )
        )
    document.sections.append(section)
    return document


def append_key_value_table_if_present(
    section: DetailSection,
    mapping: dict,
    *,
    headers: List[str],
) -> None:
    if not isinstance(mapping, dict) or not mapping:
        return
    rows: List[List[str]] = []
    for key, value in mapping.items():
        rows.append([str(key), str(value)])
    section.blocks.append(TableBlock(headers=list(headers), rows=rows))


__all__ = [
    "build_simple_title_and_description_document",
    "append_key_value_table_if_present",
    "BulletListBlock",
    "DetailDocument",
    "DetailSection",
    "ParagraphBlock",
    "ParagraphStyle",
    "TableBlock",
]


