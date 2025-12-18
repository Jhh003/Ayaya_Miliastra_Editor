from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, List, Set

from engine.graph.utils.metadata_extractor import extract_graph_variables_from_ast
from engine.nodes.node_registry import get_node_registry
from engine.type_registry import (
    BASIC_STRUCT_SUPPORTED_TYPES,
    TYPE_ENUM,
    TYPE_FLOW,
    TYPE_GENERIC,
    parse_typed_dict_alias,
)

from ...context import ValidationContext
from ...issue import EngineIssue
from ...pipeline import ValidationRule
from ..ast_utils import create_rule_issue, get_cached_module, iter_class_methods, line_span_text


_ALLOWED_TYPE_NAMES_CACHE: Dict[str, Set[str]] = {}


def _get_allowed_type_names(workspace_path: Path) -> Set[str]:
    """返回当前工作区下节点图支持的所有数据类型名称集合（含结构体/列表/端口类型）。"""
    cache_key = str(workspace_path.resolve())
    cached = _ALLOWED_TYPE_NAMES_CACHE.get(cache_key)
    if cached is not None:
        return cached

    allowed: Set[str] = set()

    # 1) 引擎内置的规范类型（基础/列表/结构体/字典）：唯一事实来源
    for type_name in BASIC_STRUCT_SUPPORTED_TYPES:
        if isinstance(type_name, str) and type_name:
            allowed.add(type_name)

    # 3) 节点端口类型（节点库中所有输入/输出/动态端口类型）
    registry = get_node_registry(workspace_path, include_composite=True)
    node_library = registry.get_library()
    for _, node_def in node_library.items():
        for port_type in getattr(node_def, "input_types", {}).values():
            if isinstance(port_type, str) and port_type:
                allowed.add(port_type)
        for port_type in getattr(node_def, "output_types", {}).values():
            if isinstance(port_type, str) and port_type:
                allowed.add(port_type)
        dynamic_type = getattr(node_def, "dynamic_port_type", "")
        if isinstance(dynamic_type, str) and dynamic_type:
            allowed.add(dynamic_type)

    # 3) 特殊端口类型与流程类型
    allowed.add(TYPE_FLOW)
    allowed.add(TYPE_GENERIC)
    # 节点库中广泛使用的“枚举”端口类型
    allowed.add(TYPE_ENUM)

    _ALLOWED_TYPE_NAMES_CACHE[cache_key] = allowed
    return allowed


class TypeNameRule(ValidationRule):
    """类型名合法性校验：节点图代码中的中文类型注解与代码级图变量声明必须使用受支持的数据类型。

    能力：
    - 检查文件顶部 GRAPH_VARIABLES 清单中声明的图变量类型名
    - 检查函数体内 AnnAssign 形式的中文字符串类型注解（例如：x: "整数" = ...）
    - 类型集合统一来源于：数据类型规则、结构体支持类型、节点库端口类型
    """

    rule_id = "engine_code_type_name"
    category = "代码规范"
    default_level = "error"

    def apply(self, ctx: ValidationContext) -> List[EngineIssue]:
        if ctx.is_composite or ctx.file_path is None:
            return []

        file_path: Path = ctx.file_path
        tree = get_cached_module(ctx)
        allowed_types = _get_allowed_type_names(ctx.workspace_path)
        issues: List[EngineIssue] = []

        # 1) 代码级 GRAPH_VARIABLES 中的图变量类型检查
        issues.extend(
            self._check_code_graph_var_types(
                tree,
                file_path,
                allowed_types,
            )
        )

        # 2) 函数体内 AnnAssign 的中文字符串类型注解检查
        for _, method in iter_class_methods(tree):
            for node in ast.walk(method):
                if not isinstance(node, ast.AnnAssign):
                    continue
                annotation = getattr(node, "annotation", None)
                if not (
                    isinstance(annotation, ast.Constant)
                    and isinstance(getattr(annotation, "value", None), str)
                ):
                    continue
                type_name = str(annotation.value).strip()
                if not type_name:
                    continue

                is_typed_dict, key_type_name, value_type_name = parse_typed_dict_alias(type_name)
                if is_typed_dict:
                    if key_type_name in allowed_types and value_type_name in allowed_types:
                        continue

                if type_name in allowed_types:
                    continue

                target = getattr(node, "target", None)
                var_name = getattr(target, "id", "") if isinstance(target, ast.Name) else ""
                var_label = f"变量『{var_name}』" if var_name else "该变量"
                message = (
                    f"{line_span_text(node)}: {var_label}使用了未知类型名『{type_name}』；"
                    "请使用节点图支持的数据类型（例如：整数、字符串、布尔值、实体、结构体等），"
                    "或在类型配置与节点定义中新增该类型后再使用。"
                )
                issues.append(
                    create_rule_issue(
                        self,
                        file_path,
                        node,
                        "CODE_UNKNOWN_TYPE_NAME",
                        message,
                    )
                )

        return issues

    def _check_code_graph_var_types(
        self,
        tree: ast.Module,
        file_path: Path,
        allowed_types: Set[str],
    ) -> List[EngineIssue]:
        """检查代码级 GRAPH_VARIABLES 声明中的图变量类型名。"""
        issues: List[EngineIssue] = []
        variables = extract_graph_variables_from_ast(tree)
        if not variables:
            return issues

        anchor_node: ast.AST = tree
        if tree.body:
            anchor_node = tree.body[0]

        for entry in variables:
            name_value = entry.get("name")
            type_value = entry.get("variable_type")
            if not isinstance(name_value, str) or not isinstance(type_value, str):
                continue

            var_name = name_value.strip()
            type_name = type_value.strip()
            if not var_name or not type_name:
                continue

            is_typed_dict, key_type_name, value_type_name = parse_typed_dict_alias(
                type_name
            )
            if is_typed_dict:
                if key_type_name in allowed_types and value_type_name in allowed_types:
                    continue

            if type_name in allowed_types:
                continue

            message = (
                f"节点图变量『{var_name}』在 GRAPH_VARIABLES 声明中使用了未知类型名『{type_name}』；"
                "请使用节点图支持的数据类型（例如：整数、字符串、布尔值、实体、结构体等），"
                "或在类型配置与节点定义中新增该类型后再使用。"
            )
            issues.append(
                create_rule_issue(
                    self,
                    file_path,
                    anchor_node,
                    "CODE_UNKNOWN_TYPE_NAME",
                    message,
                )
            )

        return issues


__all__ = ["TypeNameRule"]


