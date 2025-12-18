"""验证结果面板 - 显示存档验证结果"""

from PyQt6 import QtCore, QtGui, QtWidgets
from typing import Dict, List, Optional, Tuple

from app.ui.foundation.theme_manager import ThemeManager, Colors, Sizes
from app.ui.foundation.context_menu_builder import ContextMenuBuilder
from app.ui.panels.panel_scaffold import PanelScaffold, SectionCard
from engine.validate.comprehensive_validator import ValidationIssue


class ValidationPanel(PanelScaffold):
    """验证结果面板"""

    # 信号：跳转到错误位置
    jump_to_issue = QtCore.pyqtSignal(dict)
    # 信号：选中问题用于右侧详情面板
    issue_selected = QtCore.pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(
            parent,
            title="验证状态",
            description="查看存档综合校验与节点图源码校验结果（双击可跳转到问题来源）",
        )
        self.package_issues: List[ValidationIssue] = []
        self.graph_code_issues: List[ValidationIssue] = []
        self._package_validated = False
        self._graph_code_validated = False
        self._build_ui()
        self._update_summary()
    
    def _build_ui(self) -> None:
        self.refresh_button = QtWidgets.QPushButton("重新验证（全部）")
        self.refresh_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.refresh_button.clicked.connect(self._on_refresh_clicked)
        self.add_action_widget(self.refresh_button)

        self.validate_graphs_for_package_button = QtWidgets.QPushButton("节点图（当前存档）")
        self.validate_graphs_for_package_button.setCursor(
            QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        )
        self.validate_graphs_for_package_button.clicked.connect(
            self._on_validate_graphs_for_package_clicked
        )
        self.add_action_widget(self.validate_graphs_for_package_button)

        self.validate_graphs_all_button = QtWidgets.QPushButton("节点图（全工程）")
        self.validate_graphs_all_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self.validate_graphs_all_button.clicked.connect(self._on_validate_graphs_all_clicked)
        self.add_action_widget(self.validate_graphs_all_button)

        self.options_button = QtWidgets.QToolButton()
        self.options_button.setText("选项")
        self.options_button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        self.options_button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.PointingHandCursor))
        self._options_menu = QtWidgets.QMenu(self.options_button)
        self._strict_entity_wire_only_action = self._options_menu.addAction("严格实体入参（仅连线/事件参数）")
        self._strict_entity_wire_only_action.setCheckable(True)
        self._strict_entity_wire_only_action.setChecked(False)
        self._disable_cache_action = self._options_menu.addAction("禁用节点图校验缓存")
        self._disable_cache_action.setCheckable(True)
        self._disable_cache_action.setChecked(False)
        self._composite_struct_check_action = self._options_menu.addAction("启用复合节点结构校验（缺少数据来源/未连接）")
        self._composite_struct_check_action.setCheckable(True)
        self._composite_struct_check_action.setChecked(True)
        self.options_button.setMenu(self._options_menu)
        self.add_action_widget(self.options_button)

        self.summary_badge = self.create_status_badge(
            "ValidationSummaryBadge",
            "✅ 未验证",
        )
        self.set_status_widget(self.summary_badge)

        issues_section = SectionCard("验证问题", "按分类展示全部校验项，双击列表项可定位问题来源")

        self.tree_widget = QtWidgets.QTreeWidget()
        self.tree_widget.setHeaderLabels(["验证结果"])
        self.tree_widget.setAlternatingRowColors(True)
        self.tree_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.tree_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree_widget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self._show_context_menu)
        issues_section.add_content_widget(self.tree_widget, stretch=1)
        self.body_layout.addWidget(issues_section, 2)
        self.setMinimumWidth(260)

    def update_issues(self, issues: List[ValidationIssue]):
        """兼容入口：默认视为“存档综合校验”结果。"""
        self.update_package_issues(issues)

    def update_package_issues(self, issues: List[ValidationIssue]) -> None:
        """更新“存档综合校验”问题列表。"""
        self.package_issues = list(issues or [])
        self._package_validated = True
        self._refresh_tree()
        self._update_summary()

    def update_graph_code_issues(self, issues: List[ValidationIssue]) -> None:
        """更新“节点图源码校验”问题列表。"""
        self.graph_code_issues = list(issues or [])
        self._graph_code_validated = True
        self._refresh_tree()
        self._update_summary()

    def get_graph_code_validation_options(self) -> Tuple[bool, bool, bool]:
        """返回节点图校验选项：(strict_entity_wire_only, disable_cache, composite_struct_check_enabled)。"""
        strict_entity_wire_only = bool(self._strict_entity_wire_only_action.isChecked())
        disable_cache = bool(self._disable_cache_action.isChecked())
        composite_struct_check_enabled = bool(self._composite_struct_check_action.isChecked())
        return strict_entity_wire_only, disable_cache, composite_struct_check_enabled
    
    def _refresh_tree(self):
        """刷新树形显示"""
        expanded_states: Dict[str, bool] = {}
        for index in range(self.tree_widget.topLevelItemCount()):
            item = self.tree_widget.topLevelItem(index)
            raw_text = item.text(0)
            base_text = raw_text.split("（", 1)[0]
            expanded_states[base_text] = item.isExpanded()
        self.tree_widget.setUpdatesEnabled(False)
        self.tree_widget.clear()
        try:
            # 两个来源分组：存档综合 + 节点图源码
            sources: List[Tuple[str, bool, List[ValidationIssue]]] = [
                ("存档综合校验", self._package_validated, list(self.package_issues)),
                ("节点图源码校验", self._graph_code_validated, list(self.graph_code_issues)),
            ]

            # 未运行任何校验
            if (not self._package_validated) and (not self._graph_code_validated):
                item = QtWidgets.QTreeWidgetItem(["✅ 未验证"])
                item.setForeground(0, QtGui.QBrush(QtGui.QColor(80, 80, 80)))
                self.tree_widget.addTopLevelItem(item)
                return

            any_issue = any(bool(issue_list) for _, _, issue_list in sources)
            if not any_issue:
                item = QtWidgets.QTreeWidgetItem(["✅ 所有验证通过"])
                item.setForeground(0, QtGui.QBrush(QtGui.QColor(0, 150, 0)))
                self.tree_widget.addTopLevelItem(item)
                return

            for source_title, validated, source_issues in sources:
                if not validated:
                    group_text = f"{source_title}（未运行）"
                else:
                    error_count = sum(1 for i in source_issues if i.level == "error")
                    warning_count = sum(1 for i in source_issues if i.level == "warning")
                    info_count = sum(1 for i in source_issues if i.level == "info")
                    if (error_count + warning_count + info_count) == 0:
                        group_text = f"{source_title}（通过）"
                    else:
                        group_text = f"{source_title}（❌{error_count} ⚠️{warning_count} ℹ️{info_count}）"

                group_item = QtWidgets.QTreeWidgetItem([group_text])
                group_item.setExpanded(expanded_states.get(source_title, True))
                group_font = group_item.font(0)
                group_font.setBold(True)
                group_item.setFont(0, group_font)
                self.tree_widget.addTopLevelItem(group_item)

                if (not validated) or (not source_issues):
                    continue

                categorized: Dict[str, List[ValidationIssue]] = {}
                for issue in source_issues:
                    categorized.setdefault(issue.category, []).append(issue)

                for category in sorted(categorized.keys()):
                    category_issues = categorized[category]
                    category_item = QtWidgets.QTreeWidgetItem([f"{category} ({len(category_issues)})"])
                    category_item.setExpanded(expanded_states.get(category, True))

                    font = category_item.font(0)
                    font.setBold(True)
                    category_item.setFont(0, font)
                    group_item.addChild(category_item)

                    sorted_issues = sorted(
                        category_issues,
                        key=lambda issue: (
                            self._level_priority(issue.level),
                            str(issue.location or ""),
                        ),
                    )
                    for issue in sorted_issues:
                        icon = self._get_level_icon(issue.level)
                        location_text = str(issue.location or "(无具体位置)")
                        issue_text = f"{icon} {location_text}"
                        issue_item = QtWidgets.QTreeWidgetItem([issue_text])
                        color = self._get_level_color(issue.level)
                        issue_item.setForeground(0, QtGui.QBrush(color))
                        issue_item.setData(0, QtCore.Qt.ItemDataRole.UserRole, issue)
                        category_item.addChild(issue_item)
        finally:
            self.tree_widget.setUpdatesEnabled(True)
    
    def _update_summary(self):
        """更新摘要显示"""
        if (not self._package_validated) and (not self._graph_code_validated):
            self.summary_badge.setText("✅ 未验证")
            self.summary_badge.apply_palette(Colors.INFO_BG, Colors.TEXT_PRIMARY)
            return

        package_error = sum(1 for i in self.package_issues if i.level == "error")
        package_warning = sum(1 for i in self.package_issues if i.level == "warning")
        package_info = sum(1 for i in self.package_issues if i.level == "info")

        graph_error = sum(1 for i in self.graph_code_issues if i.level == "error")
        graph_warning = sum(1 for i in self.graph_code_issues if i.level == "warning")
        graph_info = sum(1 for i in self.graph_code_issues if i.level == "info")

        parts: List[str] = []
        if self._package_validated:
            parts.append(f"存档：❌{package_error} ⚠️{package_warning} ℹ️{package_info}")
        if self._graph_code_validated:
            parts.append(f"节点图：❌{graph_error} ⚠️{graph_warning} ℹ️{graph_info}")
        if not parts:
            parts.append("✅ 未验证")
        summary_text = " | ".join(parts)
        self.summary_badge.setText(summary_text)

        total_errors = package_error + graph_error
        total_warnings = package_warning + graph_warning
        total_infos = package_info + graph_info

        if total_errors > 0:
            self.summary_badge.apply_palette(Colors.ERROR_BG, Colors.ERROR)
        elif total_warnings > 0:
            self.summary_badge.apply_palette(Colors.BG_CARD_HOVER, Colors.WARNING)
        elif total_infos > 0:
            self.summary_badge.apply_palette(Colors.INFO_BG, Colors.INFO)
        else:
            self.summary_badge.apply_palette(Colors.SUCCESS_BG, Colors.SUCCESS)
    
    def _get_level_icon(self, level: str) -> str:
        """获取级别图标"""
        return {
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️"
        }.get(level, "·")
    
    def _get_level_color(self, level: str) -> QtGui.QColor:
        """获取级别颜色"""
        return {
            "error": QtGui.QColor(220, 50, 50),
            "warning": QtGui.QColor(230, 150, 0),
            "info": QtGui.QColor(50, 120, 200)
        }.get(level, QtGui.QColor(100, 100, 100))

    @staticmethod
    def _level_priority(level: str) -> int:
        return {"error": 0, "warning": 1, "info": 2}.get(level, 3)

    def _on_selection_changed(self) -> None:
        """选中项变化时，实时通知右侧详情面板。"""
        current_item = self.tree_widget.currentItem()
        if current_item is None:
            self.issue_selected.emit(None)
            return
        issue = current_item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if issue and isinstance(issue, ValidationIssue):
            self.issue_selected.emit(issue)
        else:
            self.issue_selected.emit(None)

    def _on_item_double_clicked(self, item: QtWidgets.QTreeWidgetItem, column: int):
        """双击项目"""
        issue = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if issue and isinstance(issue, ValidationIssue):
            # 通知外部显示详细信息
            self.issue_selected.emit(issue)

            # 发送跳转信号
            if issue.detail:
                self.jump_to_issue.emit(issue.detail)
    
    def _show_context_menu(self, pos: QtCore.QPoint):
        """显示右键菜单"""
        item = self.tree_widget.itemAt(pos)
        if not item:
            return
        
        issue = item.data(0, QtCore.Qt.ItemDataRole.UserRole)
        if not issue or not isinstance(issue, ValidationIssue):
            return
        
        builder = ContextMenuBuilder(self)
        if issue.detail:
            builder.add_action("🔍 跳转到此位置", lambda: self.jump_to_issue.emit(issue.detail))
        builder.add_action("📋 复制问题描述", lambda: self._copy_issue_text(issue))
        issue_file = getattr(issue, "file", None)
        if isinstance(issue_file, str) and issue_file:
            builder.add_action("📄 复制文件路径", lambda: self._copy_text(issue_file))
        builder.exec_for(self.tree_widget, pos)
    
    def _copy_issue_text(self, issue: ValidationIssue):
        """复制问题文本"""
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(str(issue))

    def _copy_text(self, text: str) -> None:
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(str(text))
    
    # 折叠相关行为已删除
    
    def _on_refresh_clicked(self):
        """刷新按钮点击：默认触发“存档+节点图”全量（当前存档）验证。"""
        parent_window = self.window()
        if hasattr(parent_window, "_trigger_validation_full"):
            parent_window._trigger_validation_full()
            return
        if hasattr(parent_window, "_trigger_validation"):
            parent_window._trigger_validation()
            return

    def _on_validate_graphs_for_package_clicked(self) -> None:
        parent_window = self.window()
        if not hasattr(parent_window, "_trigger_graph_code_validation"):
            return
        strict_entity_wire_only, disable_cache, composite_struct_check_enabled = (
            self.get_graph_code_validation_options()
        )
        parent_window._trigger_graph_code_validation(
            scope="package",
            strict_entity_wire_only=strict_entity_wire_only,
            disable_cache=disable_cache,
            enable_composite_struct_check=composite_struct_check_enabled,
        )

    def _on_validate_graphs_all_clicked(self) -> None:
        parent_window = self.window()
        if not hasattr(parent_window, "_trigger_graph_code_validation"):
            return
        strict_entity_wire_only, disable_cache, composite_struct_check_enabled = (
            self.get_graph_code_validation_options()
        )
        parent_window._trigger_graph_code_validation(
            scope="all",
            strict_entity_wire_only=strict_entity_wire_only,
            disable_cache=disable_cache,
            enable_composite_struct_check=composite_struct_check_enabled,
        )
    
    def clear(self):
        """清空显示"""
        self.package_issues = []
        self.graph_code_issues = []
        self._package_validated = False
        self._graph_code_validated = False
        self.tree_widget.clear()
        self._update_summary()
        self.issue_selected.emit(None)
    
    def get_error_count(self) -> int:
        """获取错误数量"""
        return sum(1 for i in self.package_issues + self.graph_code_issues if i.level == "error")
    
    def get_warning_count(self) -> int:
        """获取警告数量"""
        return sum(1 for i in self.package_issues + self.graph_code_issues if i.level == "warning")
    
    def has_errors(self) -> bool:
        """是否有错误"""
        return self.get_error_count() > 0

