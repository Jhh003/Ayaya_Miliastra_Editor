from __future__ import annotations

from pathlib import Path

from engine.nodes.composite_file_policy import (
    discover_composite_definition_files,
    get_composite_library_dir,
    is_composite_definition_file,
)
from engine.nodes.composite_node_manager import CompositeNodeManager
from engine.nodes.pipeline.composite_discovery import discover_composite_files


def _is_under_dir(path: Path, root: Path) -> bool:
    path_text = path.resolve().as_posix().rstrip("/")
    root_text = root.resolve().as_posix().rstrip("/")
    return path_text.startswith(root_text + "/")


def test_composite_definition_file_policy_single_source_of_truth() -> None:
    workspace = Path(__file__).resolve().parents[1]
    composites_dir = get_composite_library_dir(workspace)

    policy_files = discover_composite_definition_files(workspace)
    pipeline_files = discover_composite_files(workspace)

    assert policy_files == pipeline_files
    assert all(is_composite_definition_file(path) for path in policy_files)
    assert all(_is_under_dir(path, composites_dir) for path in policy_files)


def test_composite_node_manager_loads_same_files_as_policy() -> None:
    workspace = Path(__file__).resolve().parents[1]
    composites_dir = get_composite_library_dir(workspace)

    policy_files = discover_composite_definition_files(workspace)
    manager = CompositeNodeManager(workspace_path=workspace, verbose=False, base_node_library=None)

    loaded_files = sorted(manager.composite_index.values(), key=lambda p: str(p.as_posix()).lower())
    loaded_files = [path for path in loaded_files if _is_under_dir(path, composites_dir)]

    assert loaded_files == policy_files


