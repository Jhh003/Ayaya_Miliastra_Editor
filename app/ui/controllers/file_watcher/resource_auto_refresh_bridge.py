from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

from PyQt6 import QtCore

from app.ui.controllers.resource_library_auto_refresh_state_machine import (
    ResourceLibraryAutoRefreshConfig,
    ResourceLibraryAutoRefreshStateMachine,
    DirectoryChangedEvent,
    DebounceTimerFiredEvent,
    FingerprintComputeStartedEvent,
    FingerprintComputeStartRejectedEvent,
    FingerprintComputedEvent,
    RefreshStartedEvent,
    RefreshCompletedEvent,
    RecordInternalWriteEvent,
    SetEnabledEvent,
    ScheduleDebounceTimerAction,
    RequestFingerprintComputeAction,
    RequestRefreshAction,
    PeriodicRecheckEvent,
)
from engine.configs.settings import settings
from engine.resources.resource_manager import ResourceManager

from .resource_fingerprint_computer import ResourceFingerprintComputer


class ResourceAutoRefreshBridge(QtCore.QObject):
    """Qt 桥接：将资源库自动刷新状态机动作落到计时器/线程/回调。"""

    def __init__(
        self,
        resource_manager: ResourceManager,
        *,
        emit_toast: Callable[[str, str], None],
        parent: Optional[QtCore.QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._resource_manager = resource_manager
        self._emit_toast = emit_toast

        self._refresh_callback: Optional[Callable[[], None]] = None

        debounce_ms = int(getattr(settings, "RESOURCE_LIBRARY_AUTO_REFRESH_DEBOUNCE_MS", 300))
        max_delay_ms = int(getattr(settings, "RESOURCE_LIBRARY_AUTO_REFRESH_MAX_DELAY_MS", 2000))
        internal_ignore_seconds = float(getattr(settings, "RESOURCE_LIBRARY_INTERNAL_WRITE_IGNORE_SECONDS", 0.8))

        self._state_machine = ResourceLibraryAutoRefreshStateMachine(
            ResourceLibraryAutoRefreshConfig(
                debounce_ms=int(debounce_ms),
                max_delay_ms=int(max_delay_ms),
                internal_write_ignore_seconds=float(internal_ignore_seconds),
            )
        )

        self._enabled: bool = bool(getattr(settings, "RESOURCE_LIBRARY_AUTO_REFRESH_ENABLED", True))
        self._state_machine.handle_event(SetEnabledEvent(enabled=bool(self._enabled)))

        self._debounce_timer: Optional[QtCore.QTimer] = None

        self._fingerprint_thread: Optional[QtCore.QThread] = None
        self._fingerprint_computer: Optional[ResourceFingerprintComputer] = None

        self._refresh_scheduled: bool = False

        self._periodic_timer: Optional[QtCore.QTimer] = None
        self._periodic_interval_seconds: float = 0.0

    def set_refresh_callback(self, callback: Optional[Callable[[], None]]) -> None:
        self._refresh_callback = callback

    def set_enabled(self, enabled: bool) -> None:
        normalized = bool(enabled)
        self._enabled = normalized
        self._state_machine.handle_event(SetEnabledEvent(enabled=bool(normalized)))
        if not normalized:
            if self._debounce_timer is not None:
                self._debounce_timer.stop()
            self._stop_periodic_timer()
            return

    def record_internal_write(self, directory_path: Path | None = None) -> None:
        self._state_machine.handle_event(
            RecordInternalWriteEvent(
                wall_time_seconds=float(time.time()),
                directory_path=directory_path,
            )
        )

    def notify_directory_changed_path(self, directory_path: Path) -> None:
        """显式入口：目录变化已被解析为 Path。"""
        if not self._enabled:
            return
        self._handle_event(
            DirectoryChangedEvent(
                directory_path=directory_path,
                wall_time_seconds=float(time.time()),
                monotonic_time_seconds=float(time.monotonic()),
            )
        )

    def set_periodic_recheck_interval_seconds(self, seconds: float) -> None:
        interval = float(seconds)
        if interval <= 0.0:
            self._periodic_interval_seconds = 0.0
            self._stop_periodic_timer()
            return
        self._periodic_interval_seconds = interval
        self._ensure_periodic_timer()

    def enable_periodic_recheck_fallback_if_needed(self, *, add_failure_count: int) -> None:
        """当 watcher 无法覆盖全部目录时，启用周期性复核作为兜底。"""
        if not self._enabled:
            return
        if int(add_failure_count) <= 0:
            return

        # 用户显式配置优先；否则使用保守的默认值（降低漏刷新概率）。
        configured = float(getattr(settings, "RESOURCE_LIBRARY_AUTO_REFRESH_PERIODIC_RECHECK_SECONDS", 0.0))
        fallback_seconds = configured if configured > 0.0 else 5.0
        if self._periodic_interval_seconds > 0.0:
            return
        self.set_periodic_recheck_interval_seconds(float(fallback_seconds))
        self._emit_toast(
            "资源库目录监听未完全建立，已启用周期性指纹复核以降低漏刷新概率",
            "warning",
        )

    # ===== 内部：状态机动作处理 =====

    def _ensure_debounce_timer(self) -> QtCore.QTimer:
        if self._debounce_timer is None:
            timer = QtCore.QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(self._on_debounce_timer_fired)
            self._debounce_timer = timer
        return self._debounce_timer

    def _on_debounce_timer_fired(self) -> None:
        self._handle_event(DebounceTimerFiredEvent(monotonic_time_seconds=float(time.monotonic())))

    def _handle_event(self, event) -> None:
        actions = self._state_machine.handle_event(event)
        self._handle_actions(actions)

    def _handle_actions(self, actions) -> None:
        for action in actions:
            if isinstance(action, ScheduleDebounceTimerAction):
                timer = self._ensure_debounce_timer()
                timer.stop()
                timer.start(int(max(0, int(action.delay_ms))))
                continue
            if isinstance(action, RequestFingerprintComputeAction):
                started = self._start_fingerprint_compute()
                if started:
                    self._state_machine.handle_event(FingerprintComputeStartedEvent())
                else:
                    self._state_machine.handle_event(FingerprintComputeStartRejectedEvent())
                continue
            if isinstance(action, RequestRefreshAction):
                self._schedule_refresh_callback()
                continue

    def _start_fingerprint_compute(self) -> bool:
        if self._fingerprint_thread is not None:
            return False

        fingerprint_thread = QtCore.QThread(self)
        fingerprint_computer = ResourceFingerprintComputer(self._resource_manager)
        fingerprint_computer.moveToThread(fingerprint_thread)

        fingerprint_thread.started.connect(fingerprint_computer.run)
        fingerprint_computer.fingerprint_computed.connect(self._on_fingerprint_computed)
        fingerprint_computer.fingerprint_computed.connect(fingerprint_thread.quit)
        fingerprint_thread.finished.connect(fingerprint_computer.deleteLater)
        fingerprint_thread.finished.connect(fingerprint_thread.deleteLater)

        self._fingerprint_thread = fingerprint_thread
        self._fingerprint_computer = fingerprint_computer
        fingerprint_thread.start()
        return True

    def _on_fingerprint_computed(self, latest_fingerprint: str) -> None:
        self._fingerprint_thread = None
        self._fingerprint_computer = None

        baseline_fingerprint = self._resource_manager.get_resource_library_fingerprint()
        self._handle_event(
            FingerprintComputedEvent(
                latest_fingerprint=str(latest_fingerprint or ""),
                baseline_fingerprint=str(baseline_fingerprint or ""),
            )
        )

    def _schedule_refresh_callback(self) -> None:
        if self._refresh_callback is None:
            return
        if self._refresh_scheduled:
            return
        self._refresh_scheduled = True
        # 排队到事件循环，避免在 watcher 回调堆栈里同步执行重活造成重入与卡顿感。
        QtCore.QTimer.singleShot(0, self._perform_refresh_callback)

    def _perform_refresh_callback(self) -> None:
        self._refresh_scheduled = False
        refresh_callback = self._refresh_callback
        if refresh_callback is None:
            return
        self._state_machine.handle_event(RefreshStartedEvent())
        refresh_callback()
        self._state_machine.handle_event(RefreshCompletedEvent())
        self._emit_toast("资源库已更新", "info")

    # ===== 周期性复核（兜底）=====

    def _ensure_periodic_timer(self) -> None:
        if self._periodic_timer is None:
            timer = QtCore.QTimer(self)
            timer.setSingleShot(False)
            timer.timeout.connect(self._on_periodic_timer)
            self._periodic_timer = timer
        interval_ms = int(max(1000, int(self._periodic_interval_seconds * 1000.0)))
        self._periodic_timer.stop()
        self._periodic_timer.start(interval_ms)

    def _stop_periodic_timer(self) -> None:
        if self._periodic_timer is not None:
            self._periodic_timer.stop()

    def _on_periodic_timer(self) -> None:
        if not self._enabled:
            return
        self._handle_event(PeriodicRecheckEvent(monotonic_time_seconds=float(time.monotonic())))

    # ===== 清理 =====

    def cleanup(self) -> None:
        if self._debounce_timer is not None:
            self._debounce_timer.stop()
            self._debounce_timer.deleteLater()
            self._debounce_timer = None
        self._stop_periodic_timer()
        if self._periodic_timer is not None:
            self._periodic_timer.deleteLater()
            self._periodic_timer = None

        fingerprint_thread = self._fingerprint_thread
        if fingerprint_thread is not None:
            fingerprint_thread.quit()
            fingerprint_thread.wait(2000)
        self._fingerprint_thread = None
        self._fingerprint_computer = None


