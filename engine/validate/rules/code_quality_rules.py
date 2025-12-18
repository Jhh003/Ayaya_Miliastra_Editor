"""
代码质量规范规则：长连线检测、未使用输出、不可达代码等
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from ..context import ValidationContext
from ..issue import EngineIssue
from ..pipeline import ValidationRule
from .ast_utils import (
    get_cached_module,
    infer_graph_scope,
    line_span_text,
    iter_class_methods,
)
from .node_index import data_query_node_names
from engine.graph.graph_code_parser import GraphCodeParser
from engine.utils.graph.graph_utils import is_flow_port_name


class LongWireRule(ValidationRule):
    """事件源实体"长连线"检测（原生规则）
    
    启发式实现：
    - 面向类结构节点图：扫描方法内将 Name('事件源实体') 作为关键字参数传递的调用
    - 统计使用行号集合与使用次数，结合配置阈值判断是否报错
    - 阈值来自 config.THRESHOLDS：
        - LONG_WIRE_USAGE_MAX（默认 2）
        - LONG_WIRE_LINE_SPAN_MIN（默认 50 行）

    说明：
    - 不依赖 runtime 巨石类的内部状态；在引擎内独立运行
    - 由于缺乏"流程节点跨度"的精确信息，此处以源码行距近似衡量跨度
    """

    rule_id = "engine_code_long_wire"
    category = "代码规范"
    default_level = "error"

    def apply(self, ctx: ValidationContext) -> List[EngineIssue]:
        # 仅对类结构节点图（非复合）生效，且需要文件路径
        if ctx.is_composite or ctx.file_path is None:
            return []

        file_path: Path = ctx.file_path
        tree = get_cached_module(ctx)

        thresholds = (ctx.config or {}).get("THRESHOLDS", {})
        usage_max: int = int(thresholds.get("LONG_WIRE_USAGE_MAX", 2))
        line_span_min: int = int(thresholds.get("LONG_WIRE_LINE_SPAN_MIN", 50))
        issues: List[EngineIssue] = []

        for class_node, method in iter_class_methods(tree):
            param_names = [a.arg for a in method.args.args if isinstance(a, ast.arg)]
            if "事件源实体" not in param_names:
                continue

            usage_lines: List[int] = []

            for call in ast.walk(method):
                if isinstance(call, ast.Call):
                    for kw in getattr(call, "keywords", []):
                        val = getattr(kw, "value", None)
                        if isinstance(val, ast.Name) and val.id == "事件源实体":
                            line_number = getattr(val, "lineno", getattr(call, "lineno", None))
                            if isinstance(line_number, int):
                                usage_lines.append(line_number)

            usage_count = len(usage_lines)
            if usage_count <= usage_max:
                continue

            line_span = (max(usage_lines) - min(usage_lines)) if usage_lines else 0
            if line_span <= line_span_min:
                continue

            issues.append(
                EngineIssue(
                    level=self.default_level,
                    category=self.category,
                    code="CODE_EVENT_ENTITY_LONG_WIRE",
                    message=(
                        f"方法 {class_node.name}.{method.name} 内『事件源实体』作为参数被使用 {usage_count} 次，"
                        f"源码行跨度约 {line_span} 行；建议在方法内部尽早获取局部引用或拆分流程以缩短跨越。"
                    ),
                    file=str(file_path),
                    line_span=f"{min(usage_lines)}~{max(usage_lines)}" if usage_lines else None,
                    detail={
                        "class_name": class_node.name,
                        "method": method.name,
                        "usage_count": usage_count,
                        "line_span": line_span,
                    },
                )
            )

        return issues


class EventMultipleFlowOutputsRule(ValidationRule):
    """事件节点存在多条流程出边（可读性提示）

    说明：
    - 事件节点通常只作为单一流程入口；若出现多条流程线，往往意味着代码中存在多个独立的流程入口或控制流被“断开”。
    - 这不一定是错误（可能是刻意并行），但在 UI 中会显著增加阅读负担，建议人工确认。
    """

    rule_id = "engine_code_event_multiple_flow_outputs"
    category = "代码规范"
    default_level = "warning"

    def apply(self, ctx: ValidationContext) -> List[EngineIssue]:
        if ctx.is_composite or ctx.file_path is None:
            return []

        file_path: Path = ctx.file_path
        parser = GraphCodeParser(ctx.workspace_path)
        graph_model, _ = parser.parse_file(file_path)

        issues: List[EngineIssue] = []
        event_nodes = [n for n in graph_model.nodes.values() if n.category == "事件节点"]
        for event_node in event_nodes:
            flow_out_edges = [
                e
                for e in graph_model.edges.values()
                if e.src_node == event_node.id and is_flow_port_name(e.src_port)
            ]
            if len(flow_out_edges) <= 1:
                continue

            dst_titles: List[str] = []
            for edge in flow_out_edges:
                dst = graph_model.nodes.get(edge.dst_node)
                dst_titles.append(dst.title if dst else str(edge.dst_node))

            issues.append(
                EngineIssue(
                    level=self.default_level,
                    category=self.category,
                    code="CODE_EVENT_MULTIPLE_FLOW_OUTPUTS",
                    message=(
                        f"{event_node.title} 事件节点的流程出口连出了 {len(flow_out_edges)} 条流程线（目标: {', '.join(dst_titles)}）；"
                        "请确认是否确实需要多个独立流程入口。若非刻意并行，建议将后续流程显式串联，避免事件节点在 UI 中呈现多分叉入口。"
                    ),
                    file=str(file_path),
                    line_span=f"{getattr(event_node, 'source_lineno', 0)}~{getattr(event_node, 'source_end_lineno', 0) or getattr(event_node, 'source_lineno', 0)}",
                )
            )

        return issues


class UnusedQueryOutputRule(ValidationRule):
    """未使用的数据/查询输出

    检测声明了变量接收节点输出但从未使用该变量的情况。
    支持两种赋值形式：
    - 简单赋值：x = 查询(...)
    - 带类型注解的赋值：x: "类型" = 查询(...)
    """

    rule_id = "engine_code_unused_query_output"
    category = "代码规范"
    default_level = "error"

    def apply(self, ctx: ValidationContext) -> List[EngineIssue]:
        if ctx.is_composite or ctx.file_path is None:
            return []

        file_path: Path = ctx.file_path
        tree = get_cached_module(ctx)
        scope = infer_graph_scope(ctx)
        query_funcs = data_query_node_names(ctx.workspace_path, scope)
        issues: List[EngineIssue] = []

        for _, method in iter_class_methods(tree):
            assigned: Dict[str, int] = {}
            used: Set[str] = set()

            # 收集：简单赋值（x = 查询(...)）和带类型注解的赋值（x: "类型" = 查询(...)）
            for node in ast.walk(method):
                # 简单赋值：x = 查询(...)
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                    fname = getattr(getattr(node.value, "func", None), "id", None)
                    if isinstance(fname, str) and (fname in query_funcs):
                        target = _single_target_name(node.targets)
                        if target:
                            lineno = getattr(node, "lineno", 0) or 0
                            assigned[target] = lineno

                # 带类型注解的赋值：x: "类型" = 查询(...)
                if isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Call):
                    fname = getattr(getattr(node.value, "func", None), "id", None)
                    if isinstance(fname, str) and (fname in query_funcs):
                        target = node.target
                        if isinstance(target, ast.Name):
                            lineno = getattr(node, "lineno", 0) or 0
                            assigned[target.id] = lineno

            # 使用：Name Load
            for node in ast.walk(method):
                if isinstance(node, ast.Name) and isinstance(getattr(node, "ctx", None), ast.Load):
                    nm = node.id
                    if nm in assigned:
                        # 必须是赋值之后的使用才算
                        if (getattr(node, "lineno", 10**9) or 10**9) > assigned[nm]:
                            used.add(nm)

            for var, line in assigned.items():
                if var not in used:
                    issues.append(EngineIssue(
                        level=self.default_level,
                        category=self.category,
                        code="CODE_UNUSED_QUERY_OUTPUT",
                        message=f"变量 '{var}' 接收了节点输出但后续未使用；请删除该赋值语句或使用其值",
                        file=str(file_path),
                        line_span=str(line),
                    ))

        return issues


class UnreachableCodeRule(ValidationRule):
    """不可达代码（基础版）
    
    仅检测：函数顶层语句序列中，出现在 Return/Raise 之后的语句。
    不展开分支的全覆盖分析（保守）。
    """

    rule_id = "engine_code_unreachable"
    category = "代码规范"
    default_level = "error"

    def apply(self, ctx: ValidationContext) -> List[EngineIssue]:
        if ctx.is_composite or ctx.file_path is None:
            return []

        file_path: Path = ctx.file_path
        tree = get_cached_module(ctx)
        issues: List[EngineIssue] = []

        for _, method in iter_class_methods(tree):
            terminated = False
            for stmt in getattr(method, "body", []) or []:
                if terminated:
                    issues.append(EngineIssue(
                        level=self.default_level,
                        category=self.category,
                        code="CODE_UNREACHABLE_AFTER_RETURN",
                        message=f"{line_span_text(stmt)}: 该语句位于 return/raise 之后，永远不会被执行",
                        file=str(file_path),
                        line_span=line_span_text(stmt),
                    ))
                    continue
                if isinstance(stmt, (ast.Return, ast.Raise)):
                    terminated = True
        return issues


class PullEvalReevaluationHazardRule(ValidationRule):
    """拉取式执行器的“重复求值风险”提示（warning）。

    背景：
    - 一些离线/简化执行器采用 pull 语义：当某个节点需要数据输入时，会沿数据边回溯求值上游节点；
    - 若同一个【获取自定义变量】节点实例同时参与“读-改-写”，并在写入后仍被后续流程节点间接依赖，
      则在无 memoization 的 pull 执行器中可能出现：
        1) 条件/数值偏移（典型：条件用到了“写入后的新值再 +1”的结果）
        2) 非确定性（随机/时间类读取被重复触发）

    本规则专注于最常见、最可静态识别的坑：
    - 【设置自定义变量】在写入某个 (目标实体, 变量名) 之前，其“变量值”数据链路中读取了同一个
      (目标实体, 变量名) 的【获取自定义变量】；
    - 且写入之后沿流程边可达的后续流程节点仍然依赖这同一个【获取自定义变量】节点实例（node_id 相同）。

    说明：
    - 这是 warning：更推荐从“执行器语义”层面提供节点输出缓存（同一 node_id 在单次事件流内只计算一次），
      但在缓存尚未就绪时，本规则可以提前提醒作者规避。
    """

    rule_id = "engine_code_pull_eval_reevaluation_hazard"
    category = "代码规范"
    default_level = "warning"

    _CUSTOM_VAR_READ_TITLE = "获取自定义变量"
    _CUSTOM_VAR_WRITE_TITLE = "设置自定义变量"

    def apply(self, ctx: ValidationContext) -> List[EngineIssue]:
        if ctx.is_composite or ctx.file_path is None:
            return []

        graph_model = _get_or_parse_graph_model(ctx)
        if graph_model is None:
            return []

        # 快速失败：没有“设置自定义变量”则无需分析
        if not any(n.title == self._CUSTOM_VAR_WRITE_TITLE for n in graph_model.nodes.values()):
            return []

        incoming_data_edges = _build_incoming_data_edge_index(graph_model)
        flow_next_map = _build_flow_next_index(graph_model)
        data_closure_cache: Dict[str, Set[str]] = {}

        def _collect_data_upstream(node_id: str) -> Set[str]:
            cached = data_closure_cache.get(node_id)
            if cached is not None:
                return cached
            raw_visited: Set[str] = set()
            canonical_visited: Set[str] = set()
            stack: List[str] = [node_id]
            while stack:
                current = stack.pop()
                incoming = incoming_data_edges.get(current, {})
                for edge in incoming.values():
                    src_node = str(getattr(edge, "src_node", "") or "")
                    if not src_node or src_node in raw_visited:
                        continue
                    raw_visited.add(src_node)
                    canonical_visited.add(_canonicalize_node_id(graph_model, src_node))
                    stack.append(src_node)
            data_closure_cache[node_id] = canonical_visited
            return canonical_visited

        issues: List[EngineIssue] = []

        for write_node in graph_model.nodes.values():
            if write_node.title != self._CUSTOM_VAR_WRITE_TITLE:
                continue

            write_key = _custom_var_key(graph_model, incoming_data_edges, write_node.id)
            if write_key is None:
                continue

            # 识别“读-改-写同一变量”的读取节点实例（必须出现在写入节点的数据依赖闭包中）
            read_node_ids: List[str] = []
            for upstream_node_id in _collect_data_upstream(write_node.id):
                upstream_node = graph_model.nodes.get(upstream_node_id)
                if upstream_node is None:
                    continue
                if upstream_node.title != self._CUSTOM_VAR_READ_TITLE:
                    continue
                read_key = _custom_var_key(graph_model, incoming_data_edges, upstream_node_id)
                if read_key is None:
                    continue
                if read_key == write_key:
                    read_node_ids.append(upstream_node_id)

            if not read_node_ids:
                continue

            downstream_flow_nodes = _collect_downstream_flow_nodes(flow_next_map, write_node.id)
            if not downstream_flow_nodes:
                continue

            hazard_pairs: Dict[str, List[str]] = {}
            for flow_node_id in downstream_flow_nodes:
                data_dependencies = _collect_data_upstream(flow_node_id)
                for read_id in read_node_ids:
                    if read_id in data_dependencies:
                        hazard_pairs.setdefault(read_id, []).append(flow_node_id)

            if not hazard_pairs:
                continue

            # 描述目标实体/变量名的数据来源，便于定位
            entity_desc, _ = _describe_input_source(graph_model, incoming_data_edges, write_node.id, "目标实体")
            var_desc, _ = _describe_input_source(graph_model, incoming_data_edges, write_node.id, "变量名")

            read_titles: List[str] = []
            for read_id in sorted(hazard_pairs.keys()):
                read_node = graph_model.nodes.get(read_id)
                read_titles.append(f"{read_node.title if read_node else read_id}")

            downstream_titles: List[str] = []
            for read_id in sorted(hazard_pairs.keys()):
                dst_ids = hazard_pairs.get(read_id, [])
                for dst_id in dst_ids:
                    dst_node = graph_model.nodes.get(dst_id)
                    dst_title = dst_node.title if dst_node else dst_id
                    if dst_title not in downstream_titles:
                        downstream_titles.append(dst_title)
            downstream_titles_display = "、".join(downstream_titles[:6])
            if len(downstream_titles) > 6:
                downstream_titles_display += "…"

            span = _span_for_graph_nodes(graph_model, [write_node.id, *hazard_pairs.keys()])
            issues.append(
                EngineIssue(
                    level=self.default_level,
                    category=self.category,
                    code="CODE_PULL_EVAL_REEVAL_AFTER_WRITE",
                    message=(
                        "检测到『读-改-写同一自定义变量』后，后续流程节点仍依赖同一个【获取自定义变量】节点实例；"
                        "在无缓存的拉取式执行器中可能发生重复求值，导致条件/数值偏移。\n"
                        f"- 写入节点: {write_node.title}\n"
                        f"- 目标实体来源: {entity_desc}\n"
                        f"- 变量名来源: {var_desc}\n"
                        f"- 复用读取节点: {'、'.join(read_titles)}\n"
                        f"- 可能受影响的后续流程节点: {downstream_titles_display}\n"
                        "建议：为该读取链路做显式缓存（【获取局部变量】中继/拆分读取节点），"
                        "或在图结构上采用“先判定分支、再写入变量”的顺序；更推荐在执行器层实现"
                        "『同一 node_id 在单次事件流内只求值一次』的输出缓存语义。"
                    ),
                    file=str(ctx.file_path),
                    line_span=span,
                    detail={
                        "write_node_id": write_node.id,
                        "read_node_ids": list(sorted(hazard_pairs.keys())),
                        "downstream_flow_node_ids": list(sorted({i for ids in hazard_pairs.values() for i in ids})),
                        "entity_source": entity_desc,
                        "var_name_source": var_desc,
                    },
                )
            )

        return issues


def _get_or_parse_graph_model(ctx: ValidationContext):
    cached = getattr(ctx, "graph_model", None)
    if cached is not None:
        return cached
    if ctx.file_path is None:
        return None
    parser = GraphCodeParser(ctx.workspace_path)
    model, _ = parser.parse_file(ctx.file_path)
    ctx.graph_model = model
    return model


def _build_incoming_data_edge_index(graph_model) -> Dict[str, Dict[str, object]]:
    incoming: Dict[str, Dict[str, object]] = {}
    for edge in graph_model.edges.values():
        dst_port = str(getattr(edge, "dst_port", "") or "")
        if is_flow_port_name(dst_port):
            continue
        dst_node = str(getattr(edge, "dst_node", "") or "")
        if not dst_node:
            continue
        per_node = incoming.setdefault(dst_node, {})
        # 多源输入由更底层结构规则处理；这里仅取第一条作为“定位辅助”
        if dst_port not in per_node:
            per_node[dst_port] = edge
    return incoming


def _build_flow_next_index(graph_model) -> Dict[str, List[str]]:
    next_map: Dict[str, List[str]] = {}
    for edge in graph_model.edges.values():
        dst_port = str(getattr(edge, "dst_port", "") or "")
        if not is_flow_port_name(dst_port):
            continue
        src_node = str(getattr(edge, "src_node", "") or "")
        dst_node = str(getattr(edge, "dst_node", "") or "")
        if not src_node or not dst_node:
            continue
        next_map.setdefault(src_node, []).append(dst_node)
    return next_map


def _collect_downstream_flow_nodes(flow_next_map: Dict[str, List[str]], start_node_id: str) -> Set[str]:
    visited: Set[str] = set()
    queue: List[str] = [start_node_id]
    while queue:
        current = queue.pop()
        for next_node_id in flow_next_map.get(current, []):
            if next_node_id in visited:
                continue
            visited.add(next_node_id)
            queue.append(next_node_id)
    visited.discard(start_node_id)
    return visited


def _describe_input_source(
    graph_model,
    incoming_data_edges: Dict[str, Dict[str, object]],
    node_id: str,
    port_name: str,
) -> Tuple[str, str]:
    node = graph_model.nodes.get(node_id)
    incoming = incoming_data_edges.get(node_id, {}).get(port_name)
    if incoming is not None:
        src_node_id = str(getattr(incoming, "src_node", "") or "")
        src_port = str(getattr(incoming, "src_port", "") or "")
        src_node = graph_model.nodes.get(src_node_id)
        src_title = src_node.title if src_node else src_node_id
        return f"{src_title}.{src_port}", f"edge:{src_node_id}:{src_port}"
    if node is not None and port_name in (node.input_constants or {}):
        raw = node.input_constants.get(port_name)
        value_text = str(raw)
        return f"常量({value_text})", f"const:{value_text}"
    return "未绑定", "unbound"


def _custom_var_key(
    graph_model,
    incoming_data_edges: Dict[str, Dict[str, object]],
    node_id: str,
) -> Optional[Tuple[str, str]]:
    node = graph_model.nodes.get(node_id)
    if node is None:
        return None
    # 仅支持“获取/设置自定义变量”的标准端口名
    _entity_description, entity_source_key = _describe_input_source(
        graph_model, incoming_data_edges, node_id, "目标实体"
    )
    _var_name_description, variable_name_source_key = _describe_input_source(
        graph_model, incoming_data_edges, node_id, "变量名"
    )
    if entity_source_key == "unbound" or variable_name_source_key == "unbound":
        return None
    return (entity_source_key, variable_name_source_key)


def _span_for_graph_nodes(graph_model, node_ids: List[str]) -> Optional[str]:
    points: List[int] = []
    for node_id in node_ids:
        node = graph_model.nodes.get(node_id)
        if node is None:
            continue
        start_line = getattr(node, "source_lineno", 0) or 0
        end_line = getattr(node, "source_end_lineno", 0) or 0
        if isinstance(start_line, int) and start_line > 0:
            points.append(start_line)
        if isinstance(end_line, int) and end_line > 0:
            points.append(end_line)
    if not points:
        return None
    return f"{min(points)}~{max(points)}"


def _canonicalize_node_id(graph_model, node_id: str) -> str:
    """将数据节点副本（copy）规约到其 original_node_id。

    说明：
    - 布局层可能为跨块共享的数据节点创建副本（node.is_data_node_copy=True），
      以提升可读性；这些副本在结构上仍代表“同一数据源”。
    - 本规则希望识别“同一读取节点实例”的复用风险，因此需要将副本规约回原始节点，
      否则在 for/match 等多块结构中会出现漏报。
    """
    current = str(node_id or "")
    depth = 0
    while current and depth < 8:
        node = graph_model.nodes.get(current) if hasattr(graph_model, "nodes") else None
        if node is None:
            break
        if not bool(getattr(node, "is_data_node_copy", False)):
            break
        origin = str(getattr(node, "original_node_id", "") or "")
        if not origin:
            break
        current = origin
        depth += 1
    return current


def _single_target_name(targets: List[ast.expr]) -> str | None:
    """获取赋值目标名称（仅支持单个名称）"""
    if len(targets) != 1:
        return None
    tgt = targets[0]
    if isinstance(tgt, ast.Name):
        return tgt.id
    return None

