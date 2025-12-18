from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Set, Tuple

from engine.nodes.node_registry import get_node_registry
from engine.nodes.constants import ALLOWED_SCOPES


def _expand_aliases(names: Set[str]) -> Set[str]:
    if not names:
        return set()
    alias: Set[str] = set(names)
    for name in list(names):
        if "/" in name:
            alias.add(name.replace("/", ""))
    return alias


@lru_cache(maxsize=8)
def node_function_names(workspace: Path, scope: str) -> Set[str]:
    """返回指定作用域下可用的节点函数名集合（含复合节点）。"""
    scope_text = str(scope or "").strip().lower()
    if scope_text not in ALLOWED_SCOPES:
        scope_text = "server"

    registry = get_node_registry(workspace, include_composite=True)
    lib = registry.get_library()
    base_names: Set[str] = {
        nd.name for _, nd in lib.items() if nd.is_available_in_scope(scope_text)
    }
    return _expand_aliases(base_names)


@lru_cache(maxsize=8)
def boolean_node_names(workspace: Path, scope: str) -> Set[str]:
    """返回指定作用域下“输出包含布尔类型”的节点名称集合。"""
    scope_text = str(scope or "").strip().lower()
    if scope_text not in ALLOWED_SCOPES:
        scope_text = "server"

    registry = get_node_registry(workspace, include_composite=True)
    lib = registry.get_library()
    names: Set[str] = set()
    for _, node_def in lib.items():
        if not node_def.is_available_in_scope(scope_text):
            continue
        for _, port_type in (getattr(node_def, "output_types", {}) or {}).items():
            if isinstance(port_type, str) and ("布尔" in port_type):
                names.add(node_def.name)
                break
    return _expand_aliases(names)


@lru_cache(maxsize=8)
def flow_node_names(workspace: Path, scope: str) -> Set[str]:
    """返回指定作用域下包含流程端口的节点名称集合。"""
    scope_text = str(scope or "").strip().lower()
    if scope_text not in ALLOWED_SCOPES:
        scope_text = "server"

    registry = get_node_registry(workspace, include_composite=True)
    lib = registry.get_library()
    names: Set[str] = set()
    for _, node_def in lib.items():
        if not node_def.is_available_in_scope(scope_text):
            continue
        input_types = getattr(node_def, "input_types", {}) or {}
        output_types = getattr(node_def, "output_types", {}) or {}
        has_flow = (
            any((isinstance(t, str) and ("流程" in t)) for t in input_types.values())
            or any((isinstance(t, str) and ("流程" in t)) for t in output_types.values())
            or ("流程入" in (getattr(node_def, "inputs", []) or []))
            or ("流程出" in (getattr(node_def, "outputs", []) or []))
        )
        if has_flow:
            names.add(node_def.name)
    return _expand_aliases(names)


@lru_cache(maxsize=8)
def data_query_node_names(workspace: Path, scope: str) -> Set[str]:
    """返回指定作用域下“查询/运算类”节点名称集合。"""
    scope_text = str(scope or "").strip().lower()
    if scope_text not in ALLOWED_SCOPES:
        scope_text = "server"

    registry = get_node_registry(workspace, include_composite=True)
    lib = registry.get_library()
    names: Set[str] = set()
    for _, node_def in lib.items():
        if not node_def.is_available_in_scope(scope_text):
            continue
        category = getattr(node_def, "category", "") or ""
        if isinstance(category, str) and (("查询" in category) or ("运算" in category)):
            names.add(node_def.name)
    return _expand_aliases(names)


@lru_cache(maxsize=8)
def event_node_names(workspace: Path, scope: str) -> Set[str]:
    """返回所有事件节点的名称集合（按节点库中的“事件节点”类别收集）。

    说明：
    - 仅依赖引擎侧节点库，不访问 assets 或 UI；
    - 结果用于代码层校验 register_event_handler 注册的事件名是否存在。
    """
    scope_text = str(scope or "").strip().lower()
    if scope_text not in ALLOWED_SCOPES:
        scope_text = "server"

    registry = get_node_registry(workspace, include_composite=True)
    lib = registry.get_library()
    names: Set[str] = set()
    for _, node_def in lib.items():
        if not node_def.is_available_in_scope(scope_text):
            continue
        category = getattr(node_def, "category", "") or ""
        if isinstance(category, str) and ("事件" in category):
            names.add(node_def.name)
    return _expand_aliases(names)


@lru_cache(maxsize=8)
def variadic_min_args(workspace: Path, scope: str) -> Dict[str, int]:
    """返回指定作用域下可变参数节点的最少实参数要求：{函数名: 最小数量}。"""
    scope_text = str(scope or "").strip().lower()
    if scope_text not in ALLOWED_SCOPES:
        scope_text = "server"

    registry = get_node_registry(workspace, include_composite=True)
    lib = registry.get_library()
    rules: Dict[str, int] = {}
    for _, node_def in lib.items():
        if not node_def.is_available_in_scope(scope_text):
            continue
        inputs: List[str] = list(getattr(node_def, "inputs", []) or [])
        if not inputs:
            continue
        variadic_inputs: List[str] = [str(inp) for inp in inputs if "~" in str(inp)]
        if not variadic_inputs:
            continue
        rules[node_def.name] = 1 if len(variadic_inputs) == 1 else 2
    return rules


@lru_cache(maxsize=8)
def input_types_by_func(workspace: Path, scope: str) -> Dict[str, Dict[str, str]]:
    scope_text = str(scope or "").strip().lower()
    if scope_text not in ALLOWED_SCOPES:
        scope_text = "server"

    registry = get_node_registry(workspace, include_composite=True)
    lib = registry.get_library()
    result: Dict[str, Dict[str, str]] = {}
    for _, nd in lib.items():
        if not nd.is_available_in_scope(scope_text):
            continue
        result[nd.name] = dict(nd.input_types)
    return result


@lru_cache(maxsize=8)
def input_generic_constraints_by_func(workspace: Path, scope: str) -> Dict[str, Dict[str, List[str]]]:
    scope_text = str(scope or "").strip().lower()
    if scope_text not in ALLOWED_SCOPES:
        scope_text = "server"

    registry = get_node_registry(workspace, include_composite=True)
    lib = registry.get_library()
    result: Dict[str, Dict[str, List[str]]] = {}
    for _, nd in lib.items():
        if not nd.is_available_in_scope(scope_text):
            continue
        constraints = getattr(nd, "input_generic_constraints", {}) or {}
        if constraints:
            result[nd.name] = {port: list(allowed or []) for port, allowed in constraints.items()}
    return result


@lru_cache(maxsize=8)
def input_enum_options_by_func(workspace: Path, scope: str) -> Dict[str, Dict[str, List[str]]]:
    """按函数名返回输入端口的枚举候选项映射。

    结构：
        {
          "开启定点运动器": {
              "移动方式": ["瞬间移动", "匀速直线运动"],
              "参数类型": ["固定速度", "固定时间"],
          },
          ...
        }
    仅当节点定义中显式声明了 input_enum_options 时才会出现在结果中。
    """
    scope_text = str(scope or "").strip().lower()
    if scope_text not in ALLOWED_SCOPES:
        scope_text = "server"

    registry = get_node_registry(workspace, include_composite=True)
    lib = registry.get_library()
    result: Dict[str, Dict[str, List[str]]] = {}
    for _, nd in lib.items():
        if not nd.is_available_in_scope(scope_text):
            continue
        options_raw = getattr(nd, "input_enum_options", {}) or {}
        if not isinstance(options_raw, dict) or not options_raw:
            continue
        options_normalized: Dict[str, List[str]] = {}
        for port_name, candidates in options_raw.items():
            if not isinstance(port_name, str) or port_name == "":
                continue
            if isinstance(candidates, list):
                options_normalized[port_name] = [str(c) for c in candidates if str(c)]
        if options_normalized:
            result[nd.name] = options_normalized
    return result


@lru_cache(maxsize=8)
def output_types_by_func(workspace: Path, scope: str) -> Dict[str, List[str]]:
    scope_text = str(scope or "").strip().lower()
    if scope_text not in ALLOWED_SCOPES:
        scope_text = "server"

    registry = get_node_registry(workspace, include_composite=True)
    lib = registry.get_library()
    result: Dict[str, List[str]] = {}
    for _, nd in lib.items():
        if not nd.is_available_in_scope(scope_text):
            continue
        outs: List[str] = []
        for out_name in nd.outputs:
            outs.append(nd.output_types.get(out_name, ""))
        result[nd.name] = outs
    return result


@lru_cache(maxsize=8)
def output_generic_constraints_by_func(workspace: Path, scope: str) -> Dict[str, Dict[str, List[str]]]:
    scope_text = str(scope or "").strip().lower()
    if scope_text not in ALLOWED_SCOPES:
        scope_text = "server"

    registry = get_node_registry(workspace, include_composite=True)
    lib = registry.get_library()
    result: Dict[str, Dict[str, List[str]]] = {}
    for _, nd in lib.items():
        if not nd.is_available_in_scope(scope_text):
            continue
        constraints = getattr(nd, "output_generic_constraints", {}) or {}
        if constraints:
            result[nd.name] = {port: list(allowed or []) for port, allowed in constraints.items()}
    return result


def clear_node_index_caches() -> None:
    node_function_names.cache_clear()
    boolean_node_names.cache_clear()
    flow_node_names.cache_clear()
    data_query_node_names.cache_clear()
    event_node_names.cache_clear()
    variadic_min_args.cache_clear()
    input_types_by_func.cache_clear()
    input_generic_constraints_by_func.cache_clear()
    output_types_by_func.cache_clear()
    output_generic_constraints_by_func.cache_clear()
    input_enum_options_by_func.cache_clear()


