from __future__ import annotations

from typing import Any, Dict, List

from PyQt6 import QtWidgets

from app.ui.widgets.two_row_field_table_widget import TwoRowFieldTableWidget


_app = QtWidgets.QApplication.instance()
if _app is None:
    _app = QtWidgets.QApplication([])


def test_two_row_field_table_widget_load_and_get_all_fields_smoke() -> None:
    widget = TwoRowFieldTableWidget(
        supported_types=["字符串", "字符串列表", "字典", "结构体"],
    )
    captured_struct_ids: List[str] = []
    widget.struct_view_requested.connect(lambda struct_id: captured_struct_ids.append(struct_id))

    fields: List[Dict[str, Any]] = [
        {"name": "title", "type_name": "字符串", "value": "hello"},
        {"name": "items", "type_name": "字符串列表", "value": ["a", "b"]},
        {"name": "mapping", "type_name": "字典", "value": {"k": "v"}},
        {"name": "struct_field", "type_name": "结构体", "value": "DemoStruct", "readonly": True},
    ]
    widget.load_fields(fields)

    # 只读结构体字段应提供“查看”按钮并能发射信号
    struct_value_cell = widget.table.cellWidget(6, 3)
    assert struct_value_cell is not None
    view_button = struct_value_cell.findChild(QtWidgets.QPushButton)
    assert view_button is not None
    assert view_button.text() == "查看"
    view_button.click()
    assert captured_struct_ids == ["DemoStruct"]

    all_fields = widget.get_all_fields()
    assert len(all_fields) == 4
    by_name = {entry["name"]: entry for entry in all_fields}

    assert by_name["title"]["value"] == "hello"
    items_value = list(by_name["items"]["value"])
    while items_value and items_value[-1] == "":
        items_value.pop()
    assert items_value == ["a", "b"]
    assert by_name["mapping"]["value"] == {"k": "v"}
    assert by_name["struct_field"]["value"] == "DemoStruct"


def test_two_row_field_table_widget_metadata_mode_preserves_raw_value() -> None:
    widget = TwoRowFieldTableWidget(
        supported_types=["字符串", "整数"],
    )
    widget.set_value_mode("metadata")
    widget.load_fields(
        [
            {"name": "count", "type_name": "整数", "value": {"raw": 123, "display": "123"}},
        ]
    )
    all_fields = widget.get_all_fields()
    assert len(all_fields) == 1
    assert all_fields[0]["name"] == "count"
    assert all_fields[0]["value"] == 123


