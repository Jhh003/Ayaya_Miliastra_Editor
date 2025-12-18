from __future__ import annotations

import argparse
import ast
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from engine.nodes.pipeline.discovery import discover_implementation_files


def _get_call_kw_str(call_node: ast.Call, key: str) -> Optional[str]:
    for keyword in call_node.keywords:
        if keyword.arg != key:
            continue
        if isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
            return keyword.value.value
    return None


def _is_node_spec_decorator(decorator_node: ast.AST) -> bool:
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


def _find_node_spec_decorator_call(function_def: ast.FunctionDef) -> Optional[ast.Call]:
    for decorator_node in function_def.decorator_list:
        if not _is_node_spec_decorator(decorator_node):
            continue
        return decorator_node if isinstance(decorator_node, ast.Call) else None
    return None


def _contains_print_call(module_ast: ast.AST) -> bool:
    for node in ast.walk(module_ast):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "print":
            return True
    return False


def _ensure_category_with_suffix(category_text: str) -> str:
    category_clean = str(category_text or "").strip()
    if category_clean.endswith("节点"):
        return category_clean
    return f"{category_clean}节点"


def _infer_scope_and_category_from_source_file(workspace_root: Path, source_file: Path) -> tuple[str, str]:
    rel = source_file.resolve().relative_to(workspace_root.resolve())
    parts = list(rel.parts)
    # plugins/nodes/<scope>/<category>/<file>.py
    if len(parts) < 5 or parts[0] != "plugins" or parts[1] != "nodes":
        raise ValueError(f"非法节点实现路径（不符合 plugins/nodes/<scope>/<category>/*.py）: {source_file}")
    return str(parts[2]), str(parts[3])


def _lint_source_file_for_entries(
    source_file: Path,
    source_text: str,
    module_ast: ast.Module,
    *,
    workspace_root: Path,
    strict: bool,
    max_lines: int,
) -> List[str]:
    errors: List[str] = []

    line_count = len(source_text.splitlines())
    if strict and line_count >= max_lines:
        errors.append(f"{source_file}: 文件行数应 < {max_lines}（当前 {line_count} 行）")

    if _contains_print_call(module_ast):
        errors.append(f"{source_file}: 不允许使用 print()，请改用 engine.utils.logging.logger（log_info/log_warn/log_error）")

    function_defs: Dict[str, ast.FunctionDef] = {
        node.name: node for node in module_ast.body if isinstance(node, ast.FunctionDef)
    }
    node_spec_functions: List[ast.FunctionDef] = [
        fn for fn in function_defs.values() if any(_is_node_spec_decorator(d) for d in fn.decorator_list)
    ]

    if strict and len(node_spec_functions) != 1:
        errors.append(f"{source_file}: 严格模式要求且仅允许一个 @node_spec（当前 {len(node_spec_functions)} 个）")

    expected_scope, expected_category = _infer_scope_and_category_from_source_file(workspace_root, source_file)
    if expected_scope not in {"server", "client"}:
        errors.append(f"{source_file}: 非法 scope 目录名 '{expected_scope}'（期望 server/client）")

    expected_category_standard = _ensure_category_with_suffix(expected_category)

    for function_def in node_spec_functions:
        decorator_call = _find_node_spec_decorator_call(function_def)
        if decorator_call is None:
            errors.append(f"{source_file}:{function_def.name}: 缺少 @node_spec(...)")
            continue

        declared_category = _get_call_kw_str(decorator_call, "category")
        if not declared_category:
            errors.append(f"{source_file}:{function_def.name}: @node_spec 缺少 category=...")
            continue

        declared_category_standard = _ensure_category_with_suffix(declared_category)
        if declared_category_standard != expected_category_standard:
            errors.append(
                f"{source_file}:{function_def.name}: 目录类别 '{expected_category_standard}' 与 @node_spec(category='{declared_category}') 不一致"
            )

    return errors


def main(argv: Optional[Sequence[str]] = None) -> int:
    if __package__:
        from ._bootstrap import ensure_workspace_root_on_sys_path, get_workspace_root
    else:
        from _bootstrap import ensure_workspace_root_on_sys_path, get_workspace_root

    ensure_workspace_root_on_sys_path()

    parser = argparse.ArgumentParser(description="Lint plugins/nodes 节点实现（以 V2 AST 发现清单为扫描源）")
    parser.add_argument("--strict", action="store_true", help="严格模式：启用更强约束（行数、单文件单节点等）")
    parser.add_argument("--max-lines", type=int, default=300, help="严格模式下的单文件最大行数阈值（默认 300）")
    args = parser.parse_args(list(argv) if argv is not None else None)

    strict = bool(args.strict)
    max_lines = int(args.max_lines)

    workspace_root = get_workspace_root()
    target_files = discover_implementation_files(workspace_root)

    errors: List[str] = []
    for source_file in target_files:
        source_text = source_file.read_text(encoding="utf-8")
        module_ast = ast.parse(source_text, filename=str(source_file))
        errors.extend(
            _lint_source_file_for_entries(
                source_file,
                source_text,
                module_ast,
                workspace_root=workspace_root,
                strict=strict,
                max_lines=max_lines,
            )
        )

    if errors:
        for err in errors:
            print(err)
        return 1

    print("[OK] 所有 plugins/nodes 实现文件通过校验")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


