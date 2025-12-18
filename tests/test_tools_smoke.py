from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run_module(module_name: str, args: list[str] | None = None, *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, "-X", "utf8", "-m", module_name]
    if args:
        command.extend(args)
    return subprocess.run(
        command,
        cwd=str(cwd or _repo_root()),
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_tools_check_impl_node_specs_smoke() -> None:
    result = _run_module("tools.check_impl_node_specs")
    assert result.returncode == 0, f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"


def test_tools_lint_node_impls_smoke() -> None:
    result = _run_module("tools.lint_node_impls")
    assert result.returncode == 0, f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"


def test_tools_check_duplicate_config_names_smoke() -> None:
    # 默认仅输出报告不失败；CI 侧可用 --fail-on-duplicates 启用强约束
    result = _run_module("tools.check_duplicate_config_names")
    assert result.returncode == 0, f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"


def test_tools_clear_caches_rebuild_index_smoke(tmp_path: Path) -> None:
    # 在临时工作区验证：--rebuild-index 不再是“占位外壳”，且不会污染仓库工作区
    workspace_root = tmp_path / "workspace"
    (workspace_root / "assets" / "资源库").mkdir(parents=True, exist_ok=True)
    result = _run_module("tools.clear_caches", ["--root", str(workspace_root), "--rebuild-index"])
    assert result.returncode == 0, f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"


