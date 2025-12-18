from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.ui.main_window.window_navigation_events_mixin import WindowAndNavigationEventsMixin


@dataclass
class _CallRecorder:
    calls: list[str]

    def record(self, name: str) -> None:
        self.calls.append(str(name))


class _DummyCloseEvent:
    def __init__(self) -> None:
        self.accept_called = False

    def accept(self) -> None:
        self.accept_called = True


class _DummyFileWatcherManager:
    def __init__(self, recorder: _CallRecorder) -> None:
        self._recorder = recorder

    def cleanup(self) -> None:
        self._recorder.record("file_watcher.cleanup")


class _DummyPackageController:
    def __init__(self, recorder: _CallRecorder) -> None:
        self._recorder = recorder
        self.flush_current_resource_panel = self._flush

    def _flush(self) -> None:
        self._recorder.record("package.flush_current_resource_panel")

    def save_dirty_blocks(self) -> None:
        self._recorder.record("package.save_dirty_blocks")

    def save_package(self) -> None:
        # 若未来回退为全量保存，这里会让测试直接失败（我们不希望退出时无条件全量写盘）
        self._recorder.record("package.save_package")


class _DummyMainWindow(WindowAndNavigationEventsMixin):
    def __init__(self, recorder: _CallRecorder) -> None:
        self._recorder = recorder
        self.file_watcher_manager = _DummyFileWatcherManager(recorder)
        self.package_controller = _DummyPackageController(recorder)

    def _save_ui_session_state(self) -> None:
        self._recorder.record("ui_session_state.save")


def test_close_event_flushes_and_uses_dirty_blocks_save(monkeypatch: pytest.MonkeyPatch) -> None:
    from engine.configs.settings import settings

    recorder = _CallRecorder(calls=[])
    main_window = _DummyMainWindow(recorder)

    settings_save_calls: list[str] = []

    def _fake_settings_save() -> None:
        settings_save_calls.append("settings.save")

    monkeypatch.setattr(settings, "save", _fake_settings_save)

    close_event = _DummyCloseEvent()
    main_window.closeEvent(close_event)  # type: ignore[arg-type]

    assert close_event.accept_called is True
    assert settings_save_calls == ["settings.save"]

    # 核心目标：关闭阶段只做 flush + 按脏块保存，不允许退回到“无条件全量保存”
    assert recorder.calls == [
        "ui_session_state.save",
        "file_watcher.cleanup",
        "package.flush_current_resource_panel",
        "package.save_dirty_blocks",
    ]


