"""Variables tab for template/instance panel - 使用通用两行结构字段表格。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional, Sequence

from PyQt6 import QtCore, QtWidgets

from engine.graph.models.package_model import VariableConfig
from engine.graph.models.entity_templates import get_all_variable_types
from engine.utils.name_utils import generate_unique_name
from app.ui.dialogs.struct_definition_types import (
    param_type_to_canonical,
)
from app.ui.dialogs.variable_edit_dialogs import EntityVariableEditDialog
from app.ui.foundation.dialog_utils import ask_yes_no_dialog, show_warning_dialog
from app.ui.foundation.theme_manager import Sizes, ThemeManager, Colors
from app.ui.foundation.toast_notification import ToastNotification
from app.ui.foundation.toolbar_utils import apply_standard_toolbar
from app.ui.panels.template_instance.tab_base import TemplateInstanceTabBase
from app.ui.panels.template_instance.variables_external_loader import (
    load_external_variable_configs,
)
from app.ui.panels.template_instance.variables_table_widget import (
    VariablesTwoRowFieldTableWidget,
)


@dataclass(frozen=True)
class VariableRow:
    variable: VariableConfig
    source: str
    prefix: str = ""
    foreground: Optional[str] = None
    background: Optional[str] = None


class VariablesTab(TemplateInstanceTabBase):
    """变量标签页，支持继承、覆写与额外变量的展示与编辑。
    
    使用通用的两行结构字段表格组件实现内联编辑。
    """

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._is_read_only = False
        self._external_read_only = False
        self._add_button: Optional[QtWidgets.QPushButton] = None
        self._delete_button: Optional[QtWidgets.QPushButton] = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = self._init_panel_layout(
            [
                ("+ 添加自定义变量", self._add_variable),
                ("删除", self._remove_variable),
            ]
        )
        layout.setSpacing(Sizes.SPACING_SMALL)
        # 通过布局首行的工具条捕获“添加/删除”按钮，便于只读模式下统一禁用
        toolbar_item = layout.itemAt(0)
        toolbar_layout = toolbar_item.layout() if toolbar_item is not None else None
        if isinstance(toolbar_layout, QtWidgets.QHBoxLayout):
            apply_standard_toolbar(toolbar_layout)
            buttons: list[QtWidgets.QPushButton] = []
            for index in range(toolbar_layout.count()):
                widget = toolbar_layout.itemAt(index).widget()
                if isinstance(widget, QtWidgets.QPushButton):
                    buttons.append(widget)
            if len(buttons) >= 1:
                self._add_button = buttons[0]
            if len(buttons) >= 2:
                self._delete_button = buttons[1]

        # 颜色图例：帮助用户快速理解继承/覆写/额外变量的背景色含义
        legend_label = QtWidgets.QLabel(self)
        legend_label.setText(
            (
                f'<span style="background-color:{Colors.BG_MAIN}; padding:2px 6px;'
                ' border-radius:4px;">继承变量（只读）</span>'
                f'  <span style="background-color:{Colors.BG_SELECTED}; color:{Colors.PRIMARY}; padding:2px 6px;'
                ' border-radius:4px;">覆写变量</span>'
                f'  <span style="background-color:{Colors.SUCCESS_BG}; padding:2px 6px;'
                ' border-radius:4px;">额外变量</span>'
            )
        )
        legend_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        legend_label.setWordWrap(True)
        legend_label.setStyleSheet(ThemeManager.hint_text_style())
        layout.addWidget(legend_label)
        self._legend_label = legend_label

        # 使用自定义变量标签页专用的两行结构字段表格组件
        self.fields_table_widget = VariablesTwoRowFieldTableWidget(
            get_all_variable_types(),
            parent=self,
        )
        layout.addWidget(self.fields_table_widget)
        
        # 连接信号
        self.fields_table_widget.field_changed.connect(self._on_variables_changed)
        self.fields_table_widget.field_deleted.connect(self._on_field_deleted_from_table)

    def _reset_ui(self) -> None:
        self.fields_table_widget.clear_fields()

    def _refresh_ui(self) -> None:
        self._apply_struct_id_options()
        self._load_variables()

    def set_resource_manager(self, resource_manager) -> None:
        """注入 ResourceManager 并同步到内部表格组件，用于加载结构体定义。"""
        super().set_resource_manager(resource_manager)
        if hasattr(self, "fields_table_widget"):
            self.fields_table_widget.set_resource_manager(resource_manager)

    def _apply_struct_id_options(self) -> None:
        """为“结构体 / 结构体列表”变量配置结构体下拉选项。"""
        from engine.configs.specialized.struct_definitions_data import list_struct_ids

        struct_ids = list_struct_ids()
        self.fields_table_widget.set_struct_id_options(struct_ids)

    def _load_variables(self) -> None:
        self._external_read_only = self._has_external_custom_variables()
        if self._add_button is not None:
            self._add_button.setEnabled(not self._external_read_only and not self._is_read_only)
        if self._delete_button is not None:
            self._delete_button.setEnabled(not self._external_read_only and not self._is_read_only)

        fields = []
        for row_data in self._iter_variable_rows():
            # 只读模式下即便是覆写/额外变量也不允许编辑
            readonly = (row_data.source == "inherited") or self._is_read_only or self._external_read_only
            fields.append({
                "name": row_data.variable.name,
                "type_name": row_data.variable.variable_type,
                "value": self._convert_variable_to_value(row_data.variable),
                "readonly": readonly,
                "foreground": row_data.foreground,
                "background": row_data.background,
            })
        
        self.fields_table_widget.load_fields(fields)

    def _convert_variable_to_value(self, var_config: VariableConfig) -> object:
        """将 VariableConfig 的 default_value 转换为通用组件格式。"""
        default_value = var_config.default_value
        variable_type = (var_config.variable_type or "").strip()
        
        # 列表类型
        if variable_type.endswith("列表") and variable_type != "结构体列表":
            if isinstance(default_value, list):
                return [str(v) for v in default_value]
            return []
        
        # 字典类型
        if variable_type == "字典":
            if isinstance(default_value, dict):
                return default_value
            return {}
        
        # 其他类型
        return default_value if default_value is not None else ""

    # 外部变量加载 ---------------------------------------------------------
    def _has_external_custom_variables(self) -> bool:
        template_path = self._get_custom_variable_path(for_template=True)
        instance_path = self._get_custom_variable_path(for_template=False)
        return bool(template_path or instance_path)

    def _get_custom_variable_path(self, *, for_template: bool) -> str:
        if not self.current_object:
            return ""
        if for_template:
            if self.object_type == "template":
                metadata = getattr(self.current_object, "metadata", {}) or {}
                return str(metadata.get("custom_variable_file", "")).strip()
            if self.object_type == "instance":
                template_obj = self._template_for_instance(self._current_instance()) if self._current_instance() else None
                metadata = getattr(template_obj, "metadata", {}) if template_obj else {}
                if not isinstance(metadata, dict):
                    return ""
                return str(metadata.get("custom_variable_file", "")).strip()
            return ""
        # for instance
        if self.object_type == "instance":
            instance_obj = self._current_instance()
            if instance_obj:
                metadata = getattr(instance_obj, "metadata", {}) or {}
                path_text = str(metadata.get("custom_variable_file", "")).strip()
                if path_text:
                    return path_text
            template_obj = self._template_for_instance(instance_obj) if instance_obj else None
            metadata = getattr(template_obj, "metadata", {}) if template_obj else {}
            if isinstance(metadata, dict):
                return str(metadata.get("custom_variable_file", "")).strip()
        if self.object_type == "level_entity":
            metadata = getattr(self.current_object, "metadata", {}) or {}
            return str(metadata.get("custom_variable_file", "")).strip()
        return ""

    def _load_external_variable_configs(self, *, for_template: bool) -> list[VariableConfig]:
        ref_text = self._get_custom_variable_path(for_template=for_template)
        if not ref_text:
            return []

        return load_external_variable_configs(ref_text)

    def _add_variable(self) -> None:
        """直接添加一个默认变量到表格中，让用户内联编辑。"""
        if not self.current_object or not self.service:
            return
        if self._external_read_only:
            return

        # 为默认变量名称生成不重复的名字（新变量 / 新变量_1 / 新变量_2 ...）
        existing_names: list[str] = []
        for row_data in self._iter_variable_rows():
            variable_name = row_data.variable.name
            if variable_name:
                existing_names.append(variable_name)
        variable_name = generate_unique_name("新变量", existing_names)

        # 创建默认变量配置
        default_var = VariableConfig(
            name=variable_name,
            variable_type="字符串",
            default_value="",
            description="",
        )
        
        # 添加到模型
        if self.service.add_variable(self.current_object, self.object_type, default_var):
            self._load_variables()
            self.data_changed.emit()
            
            # 选中新添加的行（最后一个变量）
            table = self.fields_table_widget.table
            last_row = table.rowCount() - 2  # 最后一个变量的主行（每个变量占2行）
            if last_row >= 0:
                table.selectRow(last_row)
                table.setFocus()

    def _remove_variable(self) -> None:
        """删除按钮点击事件。"""
        if not self.current_object or not self.service:
            return
        if self._external_read_only:
            return
        
        # 获取当前选中的行
        table = self.fields_table_widget.table
        current_row = table.currentRow()
        if current_row < 0:
            return
        
        # 计算实际的变量索引
        variable_index = current_row // 2
        
        # 获取变量信息
        all_rows = list(self._iter_variable_rows())
        if variable_index >= len(all_rows):
            return
        
        row_data = all_rows[variable_index]
        self._perform_variable_deletion(row_data)

    def _on_field_deleted_from_table(self) -> None:
        """从表格右键菜单删除字段。"""
        # 右键删除通过通用组件已经完成了UI删除，但我们需要同步到数据模型
        # 重新加载以保持一致
        if not self.current_object or not self.service:
            return
        if self._external_read_only:
            return
        
        # 获取当前字段数据
        fields = self.fields_table_widget.get_all_fields()
        
        # 找出被删除的变量（对比原有变量列表）
        current_names = {f.get("name") for f in fields}
        all_vars = list(self._iter_variable_rows())
        
        for row_data in all_vars:
            if row_data.variable.name not in current_names:
                # 这个变量被删除了
                self._perform_variable_deletion(row_data)
                return

    def _perform_variable_deletion(self, row_data: VariableRow) -> None:
        """执行变量删除逻辑。"""
        if row_data.source == "inherited":
            show_warning_dialog(
                self,
                "无法删除",
                "无法删除从模板继承的变量。\n如需移除，请在模板中操作或覆写该变量。",
            )
            # 重新加载以恢复UI
            self._load_variables()
            return
        
        if row_data.source == "overridden":
            should_restore = ask_yes_no_dialog(
                self,
                "确认恢复",
                "此变量已被覆写，删除将恢复为模板值，是否继续？",
            )
            if not should_restore:
                self._load_variables()
                return
        
        if self.service.remove_variable(
            self.current_object, self.object_type, row_data.variable, row_data.source
        ):
            self._load_variables()
            self.data_changed.emit()
            ToastNotification.show_message(self, f"已删除变量 '{row_data.variable.name}'。", "success")

    def _on_variables_changed(self) -> None:
        """字段内容变化时，写回到数据模型。"""
        if not self.current_object or not self.service:
            return
        if self._external_read_only:
            return

        # 从通用组件获取所有字段（按表格当前行顺序）
        fields = self.fields_table_widget.get_all_fields()

        # 获取原始变量行列表，用于比对来源与检测删除
        all_rows = list(self._iter_variable_rows())

        # 优先处理“删除字段”场景：当表格行数减少时，通过名称差集找到被删除的变量，
        # 并复用统一的删除逻辑（包含继承/覆写提示）。
        if len(fields) < len(all_rows):
            current_names = {str(field.get("name", "")).strip() for field in fields}
            deleted_row: Optional[VariableRow] = None
            for row_data in all_rows:
                variable_name = row_data.variable.name
                if variable_name not in current_names:
                    deleted_row = row_data
                    break

            if deleted_row is not None:
                self._perform_variable_deletion(deleted_row)
                return

        # 常规内容变更：逐行比对字段，按行视为“同一条记录”，支持行内改名而不产生重复项
        for index, field in enumerate(fields):
            field_name = field.get("name", "").strip()
            type_name = field.get("type_name", "").strip()
            value = field.get("value")

            if not field_name or not type_name:
                continue

            new_variable = VariableConfig(
                name=field_name,
                variable_type=type_name,
                default_value=value,
                description="",
            )

            if index < len(all_rows):
                original_row = all_rows[index]
                original_variable = original_row.variable

                # 若名称、类型与默认值均未变化，则无需写回
                if (
                    new_variable.name == original_variable.name
                    and new_variable.variable_type == original_variable.variable_type
                    and new_variable.default_value == original_variable.default_value
                ):
                    continue

                # 发生变化：统一交由服务层原位更新，保证变量顺序稳定
                self.service.update_variable(
                    self.current_object,
                    self.object_type,
                    original_variable,
                    new_variable,
                    original_row.source,
                )
            else:
                # 表格中多出的行视为新增变量
                self.service.add_variable(
                    self.current_object,
                    self.object_type,
                    new_variable,
                )

        self.data_changed.emit()

    def _iter_variable_rows(self) -> Iterable[VariableRow]:
        """生成变量行数据，包含继承/覆写/额外变量的标记。"""
        if not self.current_object:
            return []
        template_vars, instance_vars, level_vars = self._collect_context_lists(
            template_attr="default_variables",
            instance_attr="override_variables",
            level_attr="override_variables",
        )

        external_template_vars = self._load_external_variable_configs(for_template=True)
        external_instance_vars = self._load_external_variable_configs(for_template=False)

        if external_template_vars:
            template_vars = external_template_vars
        if external_instance_vars:
            instance_vars = external_instance_vars
        if self.object_type == "template":
            for var in template_vars:
                yield VariableRow(var, "template")
            return
        if self.object_type == "level_entity":
            for var in level_vars:
                # 关卡实体上的变量等同于实例上的“额外变量”，用浅绿色底色区分
                yield VariableRow(
                    var,
                    "additional",
                    background=Colors.SUCCESS_BG,
                )
            return
        override_map = {var.name: var for var in instance_vars}
        template_var_names = {v.name for v in template_vars}
        for base_var in template_vars:
            if base_var.name in override_map:
                override_var = override_map[base_var.name]
                yield VariableRow(
                    override_var,
                    "overridden",
                    foreground=Colors.PRIMARY,
                    # 浅蓝底色提示为“覆写”变量
                    background=Colors.BG_SELECTED,
                )
            else:
                yield VariableRow(
                    base_var,
                    "inherited",
                    foreground=Colors.TEXT_SECONDARY,
                    background=Colors.BG_MAIN,
                )
        for var in instance_vars:
            if var.name in template_var_names:
                continue
            # 仅存在于实例上的变量视为“额外变量”，与关卡实体保持同一配色
            yield VariableRow(
                var,
                "additional",
                background=Colors.SUCCESS_BG,
            )

    # 只读模式 ---------------------------------------------------------------
    def set_read_only(self, read_only: bool) -> None:
        """切换变量标签页的只读状态。

        只读模式下：
        - “添加自定义变量 / 删除”按钮禁用；
        - 表格内所有变量行标记为只读，不再触发写回逻辑；
        - 仍保留滚动与查看能力（通过表格本身的启用状态控制）。
        """
        self._is_read_only = read_only
        if self._add_button is not None:
            self._add_button.setEnabled(not read_only)
        if self._delete_button is not None:
            self._delete_button.setEnabled(not read_only)
        # 禁用整体表格以避免右键删除等编辑行为；只读切换后重新加载一遍字段以应用只读标记
        self.fields_table_widget.setEnabled(not read_only)
        self._load_variables()


__all__ = ["VariablesTab"]
