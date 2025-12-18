from __future__ import annotations

import time
from collections import deque
from pathlib import Path
from typing import Deque, Optional

from PyQt6 import QtCore

from .resource_watch_dir_scanner import ResourceWatchDirScanner


class ResourceWatchRegistry(QtCore.QObject):
    """资源库目录 watcher 注册与维护。

    职责：
    - 后台扫描资源库目录树（QThread），收集目录列表；
    - 主线程分批 addPath，避免一次性 addPath 卡住 UI；
    - directoryChanged 事件触发时，增量扫描新增子目录并补齐 watcher；
    - 记录 addPath 失败次数，供上层决定是否启用“周期性指纹复核”兜底。
    """

    setup_finished = QtCore.pyqtSignal(int, int)  # watched_dir_count, add_failure_count

    def __init__(self, file_watcher: QtCore.QFileSystemWatcher, *, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._file_watcher = file_watcher

        self._enabled: bool = True

        self._watch_setup_scheduled: bool = False
        self._watch_scan_thread: Optional[QtCore.QThread] = None
        self._watch_scanner: Optional[ResourceWatchDirScanner] = None

        self._pending_watch_dirs: Deque[Path] = deque()
        self._watch_owned_dir_texts: set[str] = set()
        self._watch_owned_dirs: list[Path] = []

        self._watch_setup_started_at: float = 0.0
        self._watch_added_count: int = 0
        self._watch_add_failure_count: int = 0

        self._pending_incremental_scan_roots: Deque[Path] = deque()
        self._incremental_scan_scheduled: bool = False

        self._batch_add_limit: int = 120
        self._incremental_scan_budget: int = 80

    @property
    def add_failure_count(self) -> int:
        return int(self._watch_add_failure_count)

    @property
    def owned_watch_dir_count(self) -> int:
        return len(self._watch_owned_dirs)

    def set_enabled(self, enabled: bool) -> None:
        normalized = bool(enabled)
        if normalized == self._enabled:
            return
        self._enabled = normalized
        if not self._enabled:
            self._stop_background_scan_if_any()
            self._pending_watch_dirs.clear()
            self._pending_incremental_scan_roots.clear()
            self._incremental_scan_scheduled = False
            self._watch_setup_scheduled = False
            self._remove_owned_watch_dirs()
            return

    def schedule_initial_setup(self, resource_root: Path) -> None:
        """延后初始化资源库目录监控（非阻塞 UI）。"""
        if not self._enabled:
            return
        if self._watch_setup_scheduled:
            return
        self._watch_setup_scheduled = True
        QtCore.QTimer.singleShot(0, lambda: self._start_initial_setup(resource_root))

    def handle_directory_changed(self, changed_dir: Path) -> None:
        """记录近期触发 directoryChanged 的目录，用于增量补齐 watcher。"""
        if not self._enabled:
            return
        if not changed_dir:
            return
        self._pending_incremental_scan_roots.append(changed_dir)
        self._schedule_incremental_scan()

    # ===== 初始扫描与分批 addPath =====

    def _start_initial_setup(self, resource_root: Path) -> None:
        if not self._enabled:
            return
        if self._watch_scan_thread is not None:
            return

        self._watch_setup_started_at = time.monotonic()
        self._watch_added_count = 0
        self._watch_add_failure_count = 0

        self._watch_owned_dir_texts.clear()
        self._watch_owned_dirs.clear()

        scan_thread = QtCore.QThread(self)
        scanner = ResourceWatchDirScanner(resource_root)
        scanner.moveToThread(scan_thread)

        scan_thread.started.connect(scanner.run)
        scanner.scan_finished.connect(self._on_scanned_dir_paths)
        scanner.scan_finished.connect(scan_thread.quit)
        scan_thread.finished.connect(scanner.deleteLater)
        scan_thread.finished.connect(scan_thread.deleteLater)

        self._watch_scan_thread = scan_thread
        self._watch_scanner = scanner
        scan_thread.start()

    def _on_scanned_dir_paths(self, dir_paths: list) -> None:
        """后台扫描完成：将目录队列交给主线程分批添加。"""
        pending_dirs: Deque[Path] = deque()
        for path_value in dir_paths:
            if not isinstance(path_value, str) or not path_value:
                continue
            pending_dirs.append(Path(path_value))

        self._pending_watch_dirs.extend(pending_dirs)
        self._add_watchers_in_batches()

    def _add_watchers_in_batches(self) -> None:
        """在主线程分批添加 watcher，避免一次性 addPath 卡住 UI。"""
        if not self._enabled:
            self._pending_watch_dirs.clear()
            return

        existing_dirs = set(self._file_watcher.directories())
        added_in_batch = 0

        while self._pending_watch_dirs and added_in_batch < self._batch_add_limit:
            directory_path = self._pending_watch_dirs.popleft()
            if not directory_path.exists() or not directory_path.is_dir():
                continue

            path_text = str(directory_path)
            if path_text in self._watch_owned_dir_texts:
                continue

            if path_text in existing_dirs:
                self._watch_owned_dir_texts.add(path_text)
                self._watch_owned_dirs.append(directory_path)
                continue

            success = self._file_watcher.addPath(path_text)
            if success:
                self._watch_owned_dir_texts.add(path_text)
                self._watch_owned_dirs.append(directory_path)
                self._watch_added_count += 1
                existing_dirs.add(path_text)
            else:
                self._watch_add_failure_count += 1

            added_in_batch += 1

        if self._pending_watch_dirs:
            QtCore.QTimer.singleShot(0, self._add_watchers_in_batches)
            return

        elapsed_seconds = time.monotonic() - self._watch_setup_started_at
        print(
            "[文件监控] 资源库目录监控已建立："
            f"watched_dirs={len(self._watch_owned_dirs)}, "
            f"added_new={self._watch_added_count}, "
            f"add_failures={self._watch_add_failure_count}, "
            f"elapsed={elapsed_seconds:.2f}s"
        )

        self._watch_scan_thread = None
        self._watch_scanner = None
        self.setup_finished.emit(int(len(self._watch_owned_dirs)), int(self._watch_add_failure_count))

    # ===== 增量补齐：扫描新增子目录 =====

    def _schedule_incremental_scan(self) -> None:
        if not self._enabled:
            self._pending_incremental_scan_roots.clear()
            self._incremental_scan_scheduled = False
            return
        if self._incremental_scan_scheduled:
            return
        self._incremental_scan_scheduled = True
        QtCore.QTimer.singleShot(0, self._scan_subdirs_in_batches)

    def _scan_subdirs_in_batches(self) -> None:
        """分批扫描近期变化目录的子目录，将新目录加入 watcher 队列。"""
        if not self._enabled:
            self._pending_incremental_scan_roots.clear()
            self._incremental_scan_scheduled = False
            return

        ignored_dir_names = {
            "__pycache__",
            ".git",
            ".idea",
            ".mypy_cache",
            ".pytest_cache",
            ".vscode",
            "__MACOSX",
        }

        existing_dir_texts = set(self._file_watcher.directories())
        existing_dir_texts.update(self._watch_owned_dir_texts)
        for queued_dir in self._pending_watch_dirs:
            existing_dir_texts.add(str(queued_dir))

        scanned_count = 0
        while self._pending_incremental_scan_roots and scanned_count < self._incremental_scan_budget:
            scan_root = self._pending_incremental_scan_roots.popleft()
            scanned_count += 1
            if not scan_root.exists() or not scan_root.is_dir():
                continue

            for child in scan_root.iterdir():
                if not child.is_dir():
                    continue
                if child.name in ignored_dir_names:
                    continue
                child_text = str(child)
                if child_text in existing_dir_texts:
                    continue

                self._pending_watch_dirs.append(child)
                existing_dir_texts.add(child_text)
                # 仅对“新发现的目录”继续向下扫描，以覆盖“批量创建多级目录”的场景
                self._pending_incremental_scan_roots.append(child)

        # 追加 watcher（分批 addPath，避免 UI 卡顿）
        if self._pending_watch_dirs:
            self._add_watchers_in_batches()

        if self._pending_incremental_scan_roots:
            QtCore.QTimer.singleShot(0, self._scan_subdirs_in_batches)
            return

        self._incremental_scan_scheduled = False

    # ===== 清理 =====

    def cleanup(self) -> None:
        self._stop_background_scan_if_any()
        self._pending_watch_dirs.clear()
        self._pending_incremental_scan_roots.clear()
        self._incremental_scan_scheduled = False
        self._remove_owned_watch_dirs()

    def _stop_background_scan_if_any(self) -> None:
        scan_thread = self._watch_scan_thread
        if scan_thread is None:
            return
        scan_thread.quit()
        scan_thread.wait(2000)
        self._watch_scan_thread = None
        self._watch_scanner = None

    def _remove_owned_watch_dirs(self) -> None:
        watched_directories = set(self._file_watcher.directories())
        for directory in self._watch_owned_dirs:
            path_text = str(directory)
            if path_text in watched_directories:
                self._file_watcher.removePath(path_text)
        self._watch_owned_dirs.clear()
        self._watch_owned_dir_texts.clear()


