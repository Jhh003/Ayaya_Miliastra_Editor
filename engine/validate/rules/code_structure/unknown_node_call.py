from __future__ import annotations

import ast
from pathlib import Path
from typing import List

from ...context import ValidationContext
from ...issue import EngineIssue
from ...pipeline import ValidationRule
from ..ast_utils import create_rule_issue, get_cached_module, infer_graph_scope, iter_class_methods, line_span_text
from ..node_index import node_function_names


def _is_self_game_expr(expr: ast.AST) -> bool:
    """判断表达式是否为 self.game（Graph Code 节点调用的常见第一个参数）。"""
    if not isinstance(expr, ast.Attribute):
        return False
    if not isinstance(getattr(expr, "value", None), ast.Name):
        return False
    return expr.value.id == "self" and expr.attr == "game"


def _looks_like_node_invocation(call_node: ast.Call) -> bool:
    """启发式：仅对“像节点调用”的函数调用做未知节点名校验，避免误伤普通 Python/框架调用。

    约定：
    - 节点函数通常以 `节点名(self.game, ...)` 形式出现；
    - 若没有显式传入 `self.game`，则不在本规则范围（由其他规则/运行期暴露）。
    """
    args = list(getattr(call_node, "args", []) or [])
    if not args:
        return False
    return _is_self_game_expr(args[0])


class UnknownNodeCallRule(ValidationRule):
    """未知节点函数名校验：检测 `某函数(self.game, ...)` 形式但函数名不在节点库中。

    背景：
    - 现有多条规则只会遍历“节点库已知函数名”的调用（例如端口类型匹配、必填入参）；
    - 这会导致拼写错误或不存在的节点名（如 `字符串相等`）在校验阶段被静默跳过；
    - 本规则将这类问题提升为 error，避免“看起来像节点图，但其实根本不是节点”的代码混入资源库。
    """

    rule_id = "engine_code_unknown_node_call"
    category = "代码规范"
    default_level = "error"

    def apply(self, ctx: ValidationContext) -> List[EngineIssue]:
        if ctx.is_composite or ctx.file_path is None:
            return []

        file_path: Path = ctx.file_path
        tree = get_cached_module(ctx)
        scope = infer_graph_scope(ctx)
        known_node_names = node_function_names(ctx.workspace_path, scope)
        issues: List[EngineIssue] = []

        for _, method in iter_class_methods(tree):
            # __init__/register_handlers 中允许出现非节点调用（例如 validate_node_graph、事件注册），避免误报。
            method_name = getattr(method, "name", "")
            if method_name in {"__init__", "register_handlers"}:
                continue

            for node in ast.walk(method):
                if not isinstance(node, ast.Call):
                    continue
                func = getattr(node, "func", None)
                if not isinstance(func, ast.Name):
                    continue

                call_name = func.id
                if call_name in known_node_names:
                    continue

                if not _looks_like_node_invocation(node):
                    continue

                message = (
                    f"{line_span_text(node)}: 发现疑似节点调用『{call_name}(self.game, ...)』，"
                    f"但『{call_name}』不在当前作用域的节点库中。"
                    "请检查节点名是否拼写错误，或在节点库中选择一个已有节点替代。"
                )
                issues.append(
                    create_rule_issue(
                        self,
                        file_path,
                        node,
                        "CODE_UNKNOWN_NODE_CALL",
                        message,
                    )
                )

        return issues


__all__ = ["UnknownNodeCallRule"]


