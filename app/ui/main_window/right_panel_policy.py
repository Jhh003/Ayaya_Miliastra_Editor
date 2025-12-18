from __future__ import annotations

from typing import Any, Iterable

from app.models.view_modes import ViewMode
from app.ui.main_window.management_right_panel_registry import (
    get_management_section_right_panel_rule,
    iter_management_right_panel_tab_ids,
)


class RightPanelPolicy:
    """右侧标签联动策略：把“section/mode → tabs 显隐”集中到一个地方。"""

    def __init__(self, main_window: Any) -> None:
        self._main_window = main_window

    # === 基础能力 ==========================================================

    def set_tab_visible(self, tab_id: str, *, visible: bool, switch_to: bool = False) -> None:
        registry = getattr(self._main_window, "right_panel_registry", None)
        if registry is None:
            raise RuntimeError("RightPanelPolicy 需要 main_window.right_panel_registry 已初始化")
        registry.ensure_visible(tab_id, visible=visible, switch_to=switch_to)

    # === 管理模式：section → tabs ==========================================

    def apply_management_section(self, section_key: str | None) -> None:
        """根据管理面板 section_key 收敛右侧管理相关 tabs。"""
        current_mode = ViewMode.from_index(self._main_window.central_stack.currentIndex())
        if current_mode != ViewMode.MANAGEMENT:
            return

        if section_key is None:
            section_key = self._get_current_management_section_key()

        # 旧行为：仅根据 section_key 开启 tab，不考虑是否有条目选中。
        self.apply_management_selection(section_key, has_selection=True)

    def apply_management_selection(self, section_key: str | None, *, has_selection: bool) -> None:
        """管理模式下的 selection-aware 收敛。

        - `ui_settings` 仅依赖 section_key（界面控件组），即使无条目选中也应可见；
        - 其它专用编辑页签（signals/structs/main_camera/peripheral/equipment）仅在有有效条目选中时可见，
          避免出现“空白编辑页签残留”。
        """
        current_mode = ViewMode.from_index(self._main_window.central_stack.currentIndex())
        if current_mode != ViewMode.MANAGEMENT:
            return

        if section_key is None:
            section_key = self._get_current_management_section_key()

        # 先统一隐藏，再按注册表规则开启（避免跨 section 残留）
        for tab_id in iter_management_right_panel_tab_ids():
            self.set_tab_visible(tab_id, visible=False)

        rule = get_management_section_right_panel_rule(section_key)
        if rule is None:
            return

        should_show = (not rule.selection_required) or has_selection
        if not should_show:
            return

        if rule.on_section_enter is not None:
            rule.on_section_enter(self._main_window)
        self.set_tab_visible(rule.tab_id, visible=True)

    def _get_current_management_section_key(self) -> str | None:
        management_widget = getattr(self._main_window, "management_widget", None)
        if management_widget is None:
            return None
        getter = getattr(management_widget, "get_current_section_key", None)
        if callable(getter):
            value = getter()
            return value if isinstance(value, str) and value else None
        value = getattr(management_widget, "_last_selected_section_key", None)
        return value if isinstance(value, str) and value else None

    # === 战斗预设：上下文 → tabs ==========================================

    def set_combat_detail_tabs_visible(
        self,
        *,
        player_template: bool = False,
        player_class: bool = False,
        skill: bool = False,
        item: bool = False,
    ) -> None:
        """统一控制战斗预设详情 tabs 的存在性（避免残留空 tab）。"""
        self.set_tab_visible("player_editor", visible=player_template)
        self.set_tab_visible("player_class_editor", visible=player_class)
        self.set_tab_visible("skill_editor", visible=skill)
        self.set_tab_visible("item_editor", visible=item)

    def reset_combat_detail_tabs(self) -> None:
        self.set_combat_detail_tabs_visible(
            player_template=False,
            player_class=False,
            skill=False,
            item=False,
        )


