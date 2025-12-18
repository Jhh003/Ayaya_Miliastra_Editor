from __future__ import annotations

from PyQt6 import QtWidgets

from app.ui.dialogs.settings_dialog import SettingsDialog
from engine.configs.settings import settings
from app.ui.graph.graph_view.auto_layout.auto_layout_controller import AutoLayoutController


def test_graph_ui_verbose_setting_updates_settings_object() -> None:
    app_instance = QtWidgets.QApplication.instance()
    if app_instance is None:
        app_instance = QtWidgets.QApplication([])

    previous_verbose = settings.GRAPH_UI_VERBOSE
    previous_save = settings.save

    def _dummy_save() -> bool:
        return True

    settings.GRAPH_UI_VERBOSE = False
    settings.save = _dummy_save

    dialog = SettingsDialog(parent=None)
    assert dialog.graph_ui_verbose_checkbox.isChecked() is False

    dialog.graph_ui_verbose_checkbox.setChecked(True)
    dialog._save_and_close()

    assert settings.GRAPH_UI_VERBOSE is True

    settings.GRAPH_UI_VERBOSE = previous_verbose
    settings.save = previous_save
    dialog.close()


def test_auto_layout_prints_errors_when_verbose(monkeypatch, capsys) -> None:
    class DummyScene:
        is_composite_editor = False

    class DummyView:
        def __init__(self) -> None:
            self._scene = DummyScene()

        def scene(self):
            return self._scene

    monkeypatch.setattr(settings, "GRAPH_UI_VERBOSE", True)
    monkeypatch.setattr(
        AutoLayoutController,
        "_collect_validation_errors",
        lambda view, mappings: ["mock-error"],
    )

    AutoLayoutController.run(DummyView())

    captured = capsys.readouterr()
    assert "【自动布局】节点图存在错误" in captured.out
    assert "mock-error" in captured.out

