from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from PyQt6 import QtWidgets

from app.ui.foundation.theme_manager import ThemeManager
from app.ui.foundation.toggle_switch import ToggleSwitch


@dataclass(frozen=True)
class FormComboOption:
    """下拉选项：display 为显示文本，value 为写回模型的值。"""

    display: str
    value: str


@dataclass(frozen=True)
class FormFieldSpec:
    """声明式字段定义（schema）。

    设计目标：
    - 用“字段列表”描述表单结构，避免在业务面板里散落大量控件创建/赋值/写回逻辑；
    - 默认使用 ThemeManager 的输入/下拉/数值框样式，保持视觉一致；
    - 不承担业务校验，只负责“模型 <-> 控件”的稳定映射。
    """

    key: str
    label: str
    kind: str
    default: Any = ""
    placeholder: Optional[str] = None
    read_only: bool = False

    # 数值类字段约束
    minimum_int: int = 0
    maximum_int: int = 9999
    minimum_float: float = -9999.0
    maximum_float: float = 9999.0
    decimals: int = 2
    single_step_float: float = 0.1
    suffix: Optional[str] = None

    # plain text
    max_height: Optional[int] = None

    # combo
    combo_options: Sequence[FormComboOption] = ()

    # bool
    use_toggle_switch: bool = False

    # 自定义读写（用于“key 不等于字典字段”或复杂结构）
    get_value: Optional[Callable[[Dict[str, Any]], Any]] = None
    set_value: Optional[Callable[[Dict[str, Any], Any], None]] = None

    # 变更回调（例如同步派生字段）
    on_changed: Optional[Callable[[Any], None]] = None


class SchemaBoundForm:
    """将一组 FormFieldSpec 渲染为可嵌入面板的表单，并绑定到 dict 模型。"""

    def __init__(
        self,
        parent: QtWidgets.QWidget,
        field_specs: Sequence[FormFieldSpec],
        model: Dict[str, Any],
    ) -> None:
        self._parent = parent
        self._field_specs: List[FormFieldSpec] = list(field_specs)
        self._model: Dict[str, Any] = model
        self._key_to_widget: Dict[str, QtWidgets.QWidget] = {}

    @property
    def widgets(self) -> Dict[str, QtWidgets.QWidget]:
        return self._key_to_widget

    def set_model(self, model: Dict[str, Any]) -> None:
        self._model = model
        self.load_from_model()

    def build_into(self, form_layout: QtWidgets.QFormLayout, *, load_initial: bool = True) -> None:
        for field_spec in self._field_specs:
            widget = self._create_widget_for_field(field_spec)
            self._key_to_widget[field_spec.key] = widget
            form_layout.addRow(field_spec.label, widget)
            self._connect_change_signal(field_spec, widget)
        if load_initial:
            self.load_from_model()

    # ------------------------------------------------------------------ 绑定：模型 -> 控件

    def load_from_model(self) -> None:
        for field_spec in self._field_specs:
            widget = self._key_to_widget.get(field_spec.key)
            if widget is None:
                continue
            value = self._read_value_from_model(field_spec)
            self._apply_value_to_widget(field_spec, widget, value)

    def _read_value_from_model(self, field_spec: FormFieldSpec) -> Any:
        if field_spec.get_value is not None:
            return field_spec.get_value(self._model)
        if field_spec.key in self._model:
            return self._model.get(field_spec.key)
        return field_spec.default

    # ------------------------------------------------------------------ 绑定：控件 -> 模型

    def _write_widget_value_to_model(self, field_spec: FormFieldSpec) -> None:
        widget = self._key_to_widget.get(field_spec.key)
        if widget is None:
            return

        value = self._extract_value_from_widget(field_spec, widget)
        if field_spec.set_value is not None:
            field_spec.set_value(self._model, value)
        else:
            self._model[field_spec.key] = value

        if field_spec.on_changed is not None:
            field_spec.on_changed(value)

    # ------------------------------------------------------------------ 控件创建与样式

    def _create_widget_for_field(self, field_spec: FormFieldSpec) -> QtWidgets.QWidget:
        if field_spec.kind == "line_edit":
            editor = QtWidgets.QLineEdit(self._parent)
            editor.setStyleSheet(ThemeManager.input_style())
            if field_spec.placeholder:
                editor.setPlaceholderText(field_spec.placeholder)
            editor.setReadOnly(field_spec.read_only)
            return editor

        if field_spec.kind == "plain_text":
            editor = QtWidgets.QPlainTextEdit(self._parent)
            editor.setStyleSheet(ThemeManager.input_style())
            if field_spec.placeholder:
                editor.setPlaceholderText(field_spec.placeholder)
            if field_spec.max_height is not None:
                editor.setMaximumHeight(field_spec.max_height)
            editor.setReadOnly(field_spec.read_only)
            return editor

        if field_spec.kind == "int_spin":
            spin_box = QtWidgets.QSpinBox(self._parent)
            spin_box.setStyleSheet(ThemeManager.spin_box_style())
            spin_box.setRange(field_spec.minimum_int, field_spec.maximum_int)
            spin_box.setReadOnly(field_spec.read_only)
            return spin_box

        if field_spec.kind == "double_spin":
            spin_box = QtWidgets.QDoubleSpinBox(self._parent)
            spin_box.setStyleSheet(ThemeManager.spin_box_style())
            spin_box.setRange(field_spec.minimum_float, field_spec.maximum_float)
            spin_box.setDecimals(field_spec.decimals)
            spin_box.setSingleStep(field_spec.single_step_float)
            if field_spec.suffix:
                spin_box.setSuffix(field_spec.suffix)
            spin_box.setReadOnly(field_spec.read_only)
            return spin_box

        if field_spec.kind == "combo":
            combo_box = QtWidgets.QComboBox(self._parent)
            combo_box.setStyleSheet(ThemeManager.combo_box_style())
            for option in field_spec.combo_options:
                combo_box.addItem(option.display, option.value)
            combo_box.setEnabled(not field_spec.read_only)
            return combo_box

        if field_spec.kind == "bool":
            if field_spec.use_toggle_switch:
                toggle = ToggleSwitch(self._parent)
                toggle.setEnabled(not field_spec.read_only)
                return toggle
            check_box = QtWidgets.QCheckBox(self._parent)
            check_box.setEnabled(not field_spec.read_only)
            return check_box

        raise ValueError(f"Unsupported field kind: {field_spec.kind}")

    # ------------------------------------------------------------------ 控件赋值/取值

    def _apply_value_to_widget(
        self,
        field_spec: FormFieldSpec,
        widget: QtWidgets.QWidget,
        value: Any,
    ) -> None:
        previous_block_state = widget.blockSignals(True)

        if field_spec.kind == "line_edit" and isinstance(widget, QtWidgets.QLineEdit):
            widget.setText("" if value is None else str(value))

        elif field_spec.kind == "plain_text" and isinstance(widget, QtWidgets.QPlainTextEdit):
            widget.setPlainText("" if value is None else str(value))

        elif field_spec.kind == "int_spin" and isinstance(widget, QtWidgets.QSpinBox):
            widget.setValue(int(value) if isinstance(value, int) else int(field_spec.default or 0))

        elif field_spec.kind == "double_spin" and isinstance(widget, QtWidgets.QDoubleSpinBox):
            float_value = float(value) if isinstance(value, (int, float)) else float(field_spec.default or 0.0)
            widget.setValue(float_value)

        elif field_spec.kind == "combo" and isinstance(widget, QtWidgets.QComboBox):
            target_value = "" if value is None else str(value)
            target_index = 0
            for index in range(widget.count()):
                data_value = widget.itemData(index)
                if isinstance(data_value, str) and data_value == target_value:
                    target_index = index
                    break
            widget.setCurrentIndex(target_index)

        elif field_spec.kind == "bool":
            checked = value is True
            if hasattr(widget, "setChecked"):
                widget.setChecked(checked)

        widget.blockSignals(previous_block_state)

    def _extract_value_from_widget(self, field_spec: FormFieldSpec, widget: QtWidgets.QWidget) -> Any:
        if field_spec.kind == "line_edit" and isinstance(widget, QtWidgets.QLineEdit):
            return widget.text()

        if field_spec.kind == "plain_text" and isinstance(widget, QtWidgets.QPlainTextEdit):
            return widget.toPlainText()

        if field_spec.kind == "int_spin" and isinstance(widget, QtWidgets.QSpinBox):
            return int(widget.value())

        if field_spec.kind == "double_spin" and isinstance(widget, QtWidgets.QDoubleSpinBox):
            return float(widget.value())

        if field_spec.kind == "combo" and isinstance(widget, QtWidgets.QComboBox):
            data_value = widget.currentData()
            return data_value if isinstance(data_value, str) else ""

        if field_spec.kind == "bool" and hasattr(widget, "isChecked"):
            return widget.isChecked()

        return None

    # ------------------------------------------------------------------ 信号连接

    def _connect_change_signal(self, field_spec: FormFieldSpec, widget: QtWidgets.QWidget) -> None:
        if field_spec.kind == "line_edit" and isinstance(widget, QtWidgets.QLineEdit):
            widget.textChanged.connect(lambda _text: self._write_widget_value_to_model(field_spec))
            return

        if field_spec.kind == "plain_text" and isinstance(widget, QtWidgets.QPlainTextEdit):
            widget.textChanged.connect(lambda: self._write_widget_value_to_model(field_spec))
            return

        if field_spec.kind == "int_spin" and isinstance(widget, QtWidgets.QSpinBox):
            widget.valueChanged.connect(lambda _value: self._write_widget_value_to_model(field_spec))
            return

        if field_spec.kind == "double_spin" and isinstance(widget, QtWidgets.QDoubleSpinBox):
            widget.valueChanged.connect(lambda _value: self._write_widget_value_to_model(field_spec))
            return

        if field_spec.kind == "combo" and isinstance(widget, QtWidgets.QComboBox):
            widget.currentIndexChanged.connect(lambda _index: self._write_widget_value_to_model(field_spec))
            return

        if field_spec.kind == "bool" and hasattr(widget, "stateChanged"):
            widget.stateChanged.connect(lambda _state: self._write_widget_value_to_model(field_spec))
            return


