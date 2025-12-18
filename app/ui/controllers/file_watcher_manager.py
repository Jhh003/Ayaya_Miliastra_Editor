"""文件监控管理器 - 监控外部文件修改和冲突解决。

本模块是主窗口侧的稳定入口（facade）：
- 对外暴露 `FileWatcherManager` 信号与方法，供主窗口与控制器连接；
- 具体实现拆分到 `app.ui.controllers.file_watcher/` 内的协作组件，避免单文件承担过多职责。

资源库自动刷新链路约束（可靠性优先）：
- watcher 事件只作为“可能有外部改动”的触发源，真正是否刷新以“指纹对比”确认；
- **指纹基线不在 watcher 事件中提前推进**：只在主窗口执行完 `refresh_resource_library()`
  的“失效 + 索引重建”后由 `ResourceManager.rebuild_index()` 更新基线；
- 目录事件风暴通过“去抖 + 最大等待时间”合并，并将指纹计算放到后台线程，避免卡 UI；
- 资源库目录树支持增量补齐 watcher：当检测到新建目录时，为其追加 watcher，避免“新目录内修改漏监听”。
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, Any

from PyQt6 import QtCore, QtWidgets

from engine.configs.settings import settings
from engine.resources.resource_manager import ResourceManager

from app.ui.controllers.file_watcher.graph_file_watch_coordinator import GraphFileWatchCoordinator
from app.ui.controllers.file_watcher.resource_watch_registry import ResourceWatchRegistry
from app.ui.controllers.file_watcher.resource_auto_refresh_bridge import ResourceAutoRefreshBridge


class FileWatcherManager(QtCore.QObject):
    """文件系统监控和冲突解决管理器（主窗口门面层）。"""

    # 信号定义
    reload_graph_requested = QtCore.pyqtSignal()
    show_toast = QtCore.pyqtSignal(str, str)  # message, type
    conflict_detected = QtCore.pyqtSignal()
    graph_reloaded = QtCore.pyqtSignal(str, dict)  # graph_id, graph_data
    force_save_requested = QtCore.pyqtSignal()  # 强制保存本地版本

    def __init__(self, resource_manager: ResourceManager, parent: Optional[QtCore.QObject] = None):
        super().__init__(parent)

        self.resource_manager = resource_manager

        self.file_watcher = QtCore.QFileSystemWatcher()
        self._watcher_signals_connected: bool = True

        # 当前监控的节点图（文件 + 图 ID）
        self.current_graph_file_path: Optional[Path] = None
        self._watched_graph_id: Optional[str] = None

        self._is_cleaning_up: bool = False
        self._has_cleaned_up: bool = False

        # 回调（由主窗口注入）
        self.get_current_graph_id = None
        self.get_scene = None
        self.get_view = None
        self.on_resource_library_changed: Optional[Callable[[], None]] = None

        # 资源库自动刷新开关
        self._resource_auto_refresh_enabled: bool = bool(
            getattr(settings, "RESOURCE_LIBRARY_AUTO_REFRESH_ENABLED", True)
        )

        self._resource_watch_registry = ResourceWatchRegistry(self.file_watcher, parent=self)
        self._resource_watch_registry.setup_finished.connect(self._on_resource_watch_setup_finished)
        self._resource_auto_refresh_bridge = ResourceAutoRefreshBridge(
            self.resource_manager,
            emit_toast=self.show_toast.emit,
            parent=self,
        )
        self._resource_auto_refresh_bridge.set_enabled(bool(self._resource_auto_refresh_enabled))
        self._resource_auto_refresh_bridge.set_refresh_callback(self._refresh_resource_library_via_callback)

        self._graph_watch_coordinator = GraphFileWatchCoordinator(
            self.resource_manager,
            self.file_watcher,
            emit_toast=self.show_toast.emit,
            emit_graph_reloaded=self.graph_reloaded.emit,
            request_force_save=self.force_save_requested.emit,
            get_active_graph_id=self._get_active_graph_id,
            get_scene=self._get_current_scene,
            get_view=self._get_current_view,
            dialog_parent_provider=self._get_dialog_parent,
            parent=self,
        )

        self.file_watcher.fileChanged.connect(self._graph_watch_coordinator.on_file_changed)
        self.file_watcher.directoryChanged.connect(self._on_resource_directory_changed)

        if self._resource_auto_refresh_enabled:
            self._resource_watch_registry.set_enabled(True)
            self._resource_watch_registry.schedule_initial_setup(self.resource_manager.resource_library_dir)
    
    def setup_file_watcher(self, graph_id: str) -> None:
        """设置文件监控（带资源清理）"""
        self._watched_graph_id = graph_id or None

        if self.current_graph_file_path is not None:
            watched_files = set(self.file_watcher.files())
            current_path_text = str(self.current_graph_file_path)
            if current_path_text in watched_files:
                self.file_watcher.removePath(current_path_text)
                print(f"[文件监控] 停止监控: {self.current_graph_file_path}")
            self.current_graph_file_path = None

        if graph_id:
            file_path = self._get_graph_file_path(graph_id)
            if file_path is not None and file_path.exists():
                self.current_graph_file_path = file_path
                success = self.file_watcher.addPath(str(file_path))
                if success:
                    print(f"[文件监控] 开始监控: {file_path}")
                else:
                    print(f"[文件监控] 监控添加失败: {file_path}")
                    self.current_graph_file_path = None

        self._graph_watch_coordinator.set_watch_context(
            graph_id=self._watched_graph_id,
            graph_file_path=self.current_graph_file_path,
        )
    
    def _get_graph_file_path(self, graph_id: str) -> Optional[Path]:
        """获取节点图的文件路径"""
        if not graph_id:
            return None
        return self.resource_manager.get_graph_file_path(graph_id)

    def _on_resource_directory_changed(self, directory_path: str) -> None:
        """资源库目录发生变化（新增/删除/重命名 JSON 等）。"""
        if not self._resource_auto_refresh_enabled:
            return
        if not directory_path:
            return

        changed_dir = Path(directory_path)
        self._resource_watch_registry.handle_directory_changed(changed_dir)
        self._resource_auto_refresh_bridge.notify_directory_changed_path(changed_dir)
    
    def update_last_save_time(self) -> None:
        """更新最后保存时间（由外部在保存时调用）"""
        self._graph_watch_coordinator.update_last_save_time()

    def update_last_resource_write_time(self, directory_path: Path | None = None) -> None:
        """更新最近一次资源库内部写盘时间，用于抑制“内部写盘触发的目录事件”导致误刷新。

        Args:
            directory_path: 若提供，则仅抑制该目录（及其子目录）内的 directoryChanged 事件；
                不提供时沿用旧行为：在短窗口内抑制全部资源库目录事件（适用于整包保存等写盘风暴）。
        """
        self._resource_auto_refresh_bridge.record_internal_write(directory_path)
    
    def cleanup(self) -> None:
        """清理文件监控（防止资源泄露）"""
        if self._is_cleaning_up or self._has_cleaned_up:
            return  # 避免重复清理
        
        self._is_cleaning_up = True

        self._graph_watch_coordinator.cleanup()
        self._resource_auto_refresh_bridge.cleanup()
        self._resource_watch_registry.cleanup()

        watched_files = list(self.file_watcher.files())
        for file_path in watched_files:
            self.file_watcher.removePath(file_path)
            print(f"[文件监控] 清理监控: {file_path}")

        watched_dirs = list(self.file_watcher.directories())
        for directory_path in watched_dirs:
            self.file_watcher.removePath(directory_path)
            print(f"[文件监控] 清理目录监控: {directory_path}")

        self.current_graph_file_path = None
        self._watched_graph_id = None

        if self._watcher_signals_connected:
            self.file_watcher.fileChanged.disconnect(self._graph_watch_coordinator.on_file_changed)
            self.file_watcher.directoryChanged.disconnect(self._on_resource_directory_changed)
            self._watcher_signals_connected = False

        print("[文件监控] 资源清理完成")
        self._has_cleaned_up = True
        self._is_cleaning_up = False
    
    def set_resource_auto_refresh_enabled(self, enabled: bool) -> None:
        """启用或关闭资源库自动刷新（仅影响资源库目录监控，不影响当前图文件监控）。

        Args:
            enabled: True 启用自动刷新；False 关闭自动刷新，仅保留手动“更新”入口。
        """
        normalized_enabled = bool(enabled)
        if normalized_enabled == self._resource_auto_refresh_enabled:
            return
        
        self._resource_auto_refresh_enabled = normalized_enabled

        self._resource_auto_refresh_bridge.set_enabled(bool(normalized_enabled))
        self._resource_watch_registry.set_enabled(bool(normalized_enabled))

        if not normalized_enabled:
            return

        self._resource_watch_registry.schedule_initial_setup(self.resource_manager.resource_library_dir)
    
    def get_watched_files_count(self) -> int:
        """获取当前监控的文件数量（用于调试）"""
        return len(self.file_watcher.files())

    # ===== 内部：回调/注入适配 =====

    def _get_active_graph_id(self) -> Optional[str]:
        if callable(self.get_current_graph_id):
            return self.get_current_graph_id() or None
        return None

    def _get_current_scene(self) -> Any:
        if callable(self.get_scene):
            return self.get_scene()
        return None

    def _get_current_view(self) -> Any:
        if callable(self.get_view):
            return self.get_view()
        return None

    def _get_dialog_parent(self) -> Optional[QtWidgets.QWidget]:
        parent = self.parent()
        if isinstance(parent, QtWidgets.QWidget):
            return parent
        return QtWidgets.QApplication.activeWindow()

    def _refresh_resource_library_via_callback(self) -> None:
        refresh_callback = self.on_resource_library_changed
        if refresh_callback is None:
            return
        refresh_callback()

    def _on_resource_watch_setup_finished(self, watched_dir_count: int, add_failure_count: int) -> None:
        self._resource_auto_refresh_bridge.enable_periodic_recheck_fallback_if_needed(
            add_failure_count=int(add_failure_count)
        )
    