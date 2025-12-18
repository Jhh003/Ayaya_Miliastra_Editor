"""检查插件节点实现是否声明了 `@node_spec`。

当前仓库节点实现以 `plugins/nodes/` 为源，节点定义/发现/校验统一走 V2 AST 管线。
本脚本基于 V2 的“实现文件发现清单”做 AST 级自检：
- 每个实现文件至少包含一个带 `@node_spec(...)` 的顶层函数。

用法（推荐在仓库根目录执行）：
    python -X utf8 -m tools.check_impl_node_specs

返回非零码请直接抛错（本脚本不吞异常）。
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
from typing import List, Optional, Sequence

from engine.nodes.pipeline.discovery import discover_implementation_files


def _is_node_spec_decorator(decorator_node: ast.AST) -> bool:
    # 支持：@node_spec(...) / @engine.node_spec(...)
    if isinstance(decorator_node, ast.Call):
        func = decorator_node.func
        if isinstance(func, ast.Name):
            return func.id == "node_spec"
        if isinstance(func, ast.Attribute):
            return func.attr == "node_spec"
    if isinstance(decorator_node, ast.Name):
        return decorator_node.id == "node_spec"
    if isinstance(decorator_node, ast.Attribute):
        return decorator_node.attr == "node_spec"
    return False


def _iter_missing_node_specs(workspace_root: Path) -> List[str]:
    missing: List[str] = []

    for source_file in discover_implementation_files(workspace_root):
        source_text = source_file.read_text(encoding="utf-8")
        module_ast = ast.parse(source_text, filename=str(source_file))

        node_spec_functions: List[ast.FunctionDef] = [
            node for node in module_ast.body
            if isinstance(node, ast.FunctionDef) and any(_is_node_spec_decorator(d) for d in node.decorator_list)
        ]
        if not node_spec_functions:
            missing.append(f"{source_file}（未找到任何带 @node_spec 的顶层函数）")

    return missing


def main(argv: Optional[Sequence[str]] = None) -> int:
    # 允许 `python tools/check_impl_node_specs.py` 与 `python -m tools.check_impl_node_specs`
    if __package__:
        from ._bootstrap import ensure_workspace_root_on_sys_path, get_workspace_root
    else:
        from _bootstrap import ensure_workspace_root_on_sys_path, get_workspace_root

    ensure_workspace_root_on_sys_path()

    parser = argparse.ArgumentParser(description="检查 plugins/nodes 实现文件是否声明 @node_spec（V2 发现清单）")
    _ = parser.parse_args(list(argv) if argv is not None else None)

    workspace_root = get_workspace_root()
    missing = _iter_missing_node_specs(workspace_root)

    if missing:
        print("[ERROR] 以下节点实现缺少 @node_spec 或注册表引用错误：")
        for item in missing:
            print(f"  - {item}")
        return 1

    print("[OK] 所有 plugins/nodes 实现文件均包含 @node_spec 顶层函数")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


