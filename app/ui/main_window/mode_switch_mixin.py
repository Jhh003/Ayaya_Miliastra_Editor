"""模式切换 Mixin：主窗口的 UI 信号入口（尽量薄）。

约定：
- 模式切换公共流程由 `ModeTransitionService` 作为单一入口执行；
- 右侧面板合同对外只暴露 `main_window.right_panel`（RightPanelController）。
"""
from __future__ import annotations

from app.ui.main_window.mode_transition_service import ModeTransitionRequest


class ModeSwitchMixin:
    """模式切换相关方法的Mixin"""

    def _update_right_panel_visibility(self) -> None:
        """兼容入口：库页在“无选中”时可能会调用该钩子以刷新右侧容器可见性。"""
        self.right_panel.update_visibility()

    def _switch_to_validation_and_validate(self) -> None:
        """切换到验证页面（F5快捷键）。

        实际的验证逻辑在进入验证模式时由 `_on_mode_changed` 统一触发，
        以便与通过导航栏切换到验证页面的行为保持一致。
        """
        self.nav_bar.set_current_mode("validation")
        self._on_mode_changed("validation")

    def _on_mode_changed(self, mode: str) -> None:
        """模式切换主入口：委托给 ModeTransitionService 执行公共流程。"""
        self.mode_transition_service.transition(self, ModeTransitionRequest(mode_string=mode))

