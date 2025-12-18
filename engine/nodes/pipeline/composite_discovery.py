from __future__ import annotations

from pathlib import Path
from typing import List

from engine.nodes.composite_file_policy import discover_composite_definition_files


def discover_composite_files(workspace_path: Path) -> List[Path]:
    """
    发现复合节点定义文件（不导入）。

    路径约定：工作区下 `assets/资源库/复合节点库/**/composite_*.py`
    """
    return discover_composite_definition_files(workspace_path)

