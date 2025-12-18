from __future__ import annotations

from pathlib import Path
from typing import List


COMPOSITE_DEFINITION_PREFIX = "composite_"


def is_composite_definition_file(path: Path) -> bool:
    """
    判断给定路径是否为“复合节点定义文件”。

    约定（与 `assets/资源库/复合节点库/claude.md` 保持一致）：
    - 必须为 *.py
    - 文件名以 `composite_` 开头（与 composite_id、落盘文件名保持一致）
    - 跳过 `__init__.py`、以下划线开头文件、以及包含“校验”的辅助脚本
    """
    if not isinstance(path, Path):
        raise TypeError("path 必须是 pathlib.Path 实例")
    if path.suffix != ".py":
        return False
    if path.name == "__init__.py":
        return False
    if path.name.startswith("_"):
        return False
    if "校验" in path.stem:
        return False
    return path.name.startswith(COMPOSITE_DEFINITION_PREFIX)


def get_composite_library_dir(workspace_path: Path) -> Path:
    if not isinstance(workspace_path, Path):
        raise TypeError("workspace_path 必须是 pathlib.Path 实例")
    root = workspace_path.resolve()
    return (root / "assets" / "资源库" / "复合节点库").resolve()


def discover_composite_definition_files(workspace_path: Path) -> List[Path]:
    """
    发现工作区中的复合节点定义文件（不导入）。

    扫描范围：
    - `assets/资源库/复合节点库/**/composite_*.py`
    """
    composites_dir = get_composite_library_dir(workspace_path)
    if not composites_dir.exists():
        return []
    files: List[Path] = []
    for py in composites_dir.rglob("composite_*.py"):
        if not is_composite_definition_file(py):
            continue
        files.append(py)
    # 稳定排序
    return sorted(files, key=lambda p: str(p.as_posix()).lower())


