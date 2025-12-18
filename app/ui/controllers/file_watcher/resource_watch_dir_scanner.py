from __future__ import annotations

from pathlib import Path

from PyQt6 import QtCore


class ResourceWatchDirScanner(QtCore.QObject):
    """后台线程：扫描资源库目录树，生成需要被监控的目录列表。

    设计目标：
    - 避免在主线程内执行 `Path.rglob()` 等可能耗时的 IO 扫描；
    - 仅负责“收集路径”，不触碰 `QFileSystemWatcher`（后者必须在主线程操作）。
    """

    scan_finished = QtCore.pyqtSignal(list)  # list[str]，每项为目录路径字符串

    def __init__(self, resource_root: Path) -> None:
        super().__init__()
        self._resource_root = resource_root

    @QtCore.pyqtSlot()
    def run(self) -> None:
        resource_root = self._resource_root
        if not resource_root.exists():
            self.scan_finished.emit([])
            return

        # 需要递归监控的根目录列表（尽量覆盖资源库主要入口）
        root_dirs_to_watch: list[Path] = [
            resource_root,
            resource_root / "实例",
            resource_root / "元件库",
            resource_root / "管理配置",
            resource_root / "战斗预设",
            resource_root / "节点图",
            resource_root / "复合节点库",
            resource_root / "功能包索引",
        ]

        ignored_dir_names = {
            "__pycache__",
            ".git",
            ".idea",
            ".mypy_cache",
            ".pytest_cache",
            ".vscode",
            "__MACOSX",
        }

        candidate_dirs: list[str] = []
        for root_dir in root_dirs_to_watch:
            if not root_dir.exists() or not root_dir.is_dir():
                continue
            candidate_dirs.append(str(root_dir))
            for sub_dir in root_dir.rglob("*"):
                if not sub_dir.is_dir():
                    continue
                if sub_dir.name in ignored_dir_names:
                    continue
                candidate_dirs.append(str(sub_dir))

        # 去重（保持大致顺序即可）
        unique_dirs: list[str] = list(dict.fromkeys(candidate_dirs))
        self.scan_finished.emit(unique_dirs)


