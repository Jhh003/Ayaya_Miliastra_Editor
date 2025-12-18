from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any, Sequence, Mapping
from collections import defaultdict
from datetime import datetime
import re

from engine.nodes.node_definition_loader import NodeDef
from engine.nodes.node_registry import get_node_registry
from engine.graph.models import GraphModel, NodeModel, PortModel
from engine.graph.common import (
    is_flow_port,
    SIGNAL_LISTEN_NODE_TITLE,
    SIGNAL_NAME_PORT_NAME,
    STRUCT_NODE_TITLES,
    STRUCT_SPLIT_NODE_TITLE,
    STRUCT_BUILD_NODE_TITLE,
    STRUCT_MODIFY_NODE_TITLE,
    STRUCT_SPLIT_STATIC_INPUTS,
    STRUCT_SPLIT_STATIC_OUTPUTS,
    STRUCT_BUILD_STATIC_INPUTS,
    STRUCT_BUILD_STATIC_OUTPUTS,
    STRUCT_MODIFY_STATIC_INPUTS,
    STRUCT_MODIFY_STATIC_OUTPUTS,
    STRUCT_NAME_PORT_NAME,
)
from importlib import import_module
from engine.nodes.port_type_system import is_flow_port_with_context
from engine.graph.utils.metadata_extractor import extract_metadata_from_code
from engine.graph.utils.ast_utils import is_class_structure_format
from engine.graph.utils.comment_extractor import extract_comments, associate_comments_to_nodes
from engine.graph.code_to_graph_orchestrator import CodeToGraphParser
from engine.graph.composite.param_usage_tracker import ParamUsageTracker
from engine.graph.ir.ast_scanner import find_graph_class
from engine.utils.name_utils import dedupe_preserve_order


"""节点图代码（Graph Code）解析工具集。

提供从类结构 Python 文件到 `GraphModel` 的解析能力，委托 `CodeToGraphParser` 和 utils 工具。
设计为**静态建模 + 校验**组件：只关心“用哪些节点、如何连线、元数据和注释”，不会执行节点实际业务逻辑，主要用于给 AI / 开发者提供可验证的节点图代码接口。
"""


# ============================================================================
# 验证函数（保持不变）
# ============================================================================

def validate_graph(
    model: GraphModel,
    virtual_pin_mappings: Optional[Dict[Tuple[str, str], bool]] = None,
    *,
    workspace_path: Optional[Path] = None,
    node_library: Optional[Dict[str, NodeDef]] = None,
) -> List[str]:
    """验证图的完整性（简化版本）
    
    Args:
        model: 节点图模型
        virtual_pin_mappings: 虚拟引脚映射 {(node_id, port_name): is_input}
                             用于复合节点编辑器，标记哪些端口已暴露为虚拟引脚
        workspace_path: 工作区路径（可选，未提供 node_library 时用于加载节点库）
        node_library: 预加载的节点库（可选，避免重复加载）
    
    Returns:
        错误列表
    """
    errors: List[str] = []
    virtual_pin_mappings = virtual_pin_mappings or {}
    
    # 获取节点库（用于端口类型查询）
    if node_library is None:
        workspace = workspace_path or Path(__file__).resolve().parents[2]
        registry = get_node_registry(workspace)
        node_library = registry.get_library()
    
    incoming_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for edge in model.edges.values():
        incoming_counts[edge.dst_node][edge.dst_port] += 1
    
    def _is_flow(node: NodeModel, port_name: str, is_source: bool) -> bool:
        return is_flow_port_with_context(node, port_name, is_source, node_library)
    
    # 检查端口类型匹配：流程端口不能连接到数据端口
    # 说明：使用集中式的上下文感知判定，覆盖"多分支"等语义特殊节点。

    for edge in model.edges.values():
        src_node = model.nodes.get(edge.src_node)
        dst_node = model.nodes.get(edge.dst_node)

        if not src_node or not dst_node:
            continue

        # 判断源端口和目标端口的类型（结合节点上下文和节点库定义）
        src_is_flow = _is_flow(src_node, edge.src_port, True)
        dst_is_flow = _is_flow(dst_node, edge.dst_port, False)

        # 流程端口和数据端口不能互连
        if src_is_flow != dst_is_flow:
            src_type = "流程端口" if src_is_flow else "数据端口"
            dst_type = "流程端口" if dst_is_flow else "数据端口"
            # 计算源/目标节点的源代码行范围（若有）
            src_lo = getattr(src_node, 'source_lineno', 0) if src_node else 0
            src_hi = getattr(src_node, 'source_end_lineno', 0) if src_node else 0
            dst_lo = getattr(dst_node, 'source_lineno', 0) if dst_node else 0
            dst_hi = getattr(dst_node, 'source_end_lineno', 0) if dst_node else 0
            lo_candidates = [x for x in [src_lo, dst_lo] if isinstance(x, int) and x > 0]
            hi_candidates = [x for x in [src_hi or src_lo, dst_hi or dst_lo] if isinstance(x, int) and x > 0]
            if lo_candidates and hi_candidates:
                span_lo = min(lo_candidates)
                span_hi = max(hi_candidates)
                span_text = f" (第{span_lo}~{span_hi}行)"
            else:
                span_text = " (第?~?行)"
            errors.append(
                f"端口类型不匹配：{src_node.title}.{edge.src_port}({src_type}) → "
                f"{dst_node.title}.{edge.dst_port}({dst_type}){span_text}"
            )
    
    for node in model.nodes.values():
        # 流程入口校验（事件节点除外）
        if node.category != '事件节点':
            incoming = incoming_counts.get(node.id, {})
            for port in node.inputs:
                if _is_flow(node, port.name, False) and port.name != '跳出循环':
                    in_count = incoming.get(port.name, 0)
                    is_virtual_pin = virtual_pin_mappings.get((node.id, port.name), False)
                    if in_count == 0 and not is_virtual_pin:
                        lo = getattr(node, 'source_lineno', 0)
                        hi = getattr(node, 'source_end_lineno', 0) or lo
                        span_text = f" (第{lo}~{hi}行)" if isinstance(lo, int) and lo > 0 else " (第?~?行)"
                        errors.append(f"节点 {node.category}/{node.title} 的流程入口 '{port.name}' 未连接{span_text}")
        
        incoming = incoming_counts.get(node.id, {})
        for port in node.inputs:
            if not _is_flow(node, port.name, False):
                has_incoming_edge = incoming.get(port.name, 0) > 0
                has_constant_value = port.name in node.input_constants
                is_virtual_pin = virtual_pin_mappings.get((node.id, port.name), False)
                if not (has_incoming_edge or has_constant_value or is_virtual_pin):
                    # 结构体节点（拆分/拼装/修改）：
                    # UI 中允许通过“结构体绑定元数据”或“已出现动态字段端口”来隐式确定结构体，
                    # 此时源码未显式传入“结构体名”也应视为已配置，避免误报缺线。
                    if (
                        getattr(node, "title", "") in STRUCT_NODE_TITLES
                        and port.name == STRUCT_NAME_PORT_NAME
                    ):
                        bound = getattr(model, "get_node_struct_binding", None)
                        has_binding = False
                        if callable(bound):
                            payload = bound(node.id)
                            has_binding = isinstance(payload, dict) and bool(payload)

                        if has_binding:
                            continue

                        # 若存在任一“非静态输入端口”（字段端口），也视为已绑定结构体。
                        static_inputs = set()
                        if getattr(node, "title", "") == STRUCT_MODIFY_NODE_TITLE:
                            static_inputs = set(STRUCT_MODIFY_STATIC_INPUTS)
                        elif getattr(node, "title", "") == STRUCT_BUILD_NODE_TITLE:
                            static_inputs = set(STRUCT_BUILD_STATIC_INPUTS)
                        elif getattr(node, "title", "") == STRUCT_SPLIT_NODE_TITLE:
                            static_inputs = set(STRUCT_SPLIT_STATIC_INPUTS)

                        has_dynamic_field_port = any(
                            (getattr(p, "name", "") not in static_inputs)
                            and (not _is_flow(node, getattr(p, "name", ""), False))
                            for p in (node.inputs or [])
                        )
                        if has_dynamic_field_port:
                            continue

                    lo = getattr(node, 'source_lineno', 0)
                    hi = getattr(node, 'source_end_lineno', 0) or lo
                    span_text = f" (第{lo}~{hi}行)" if isinstance(lo, int) and lo > 0 else " (第?~?行)"
                    errors.append(f"节点 {node.category}/{node.title} 的输入端 \"{port.name}\" 缺少数据来源{span_text}")
    
    return errors


# ============================================================================
# 节点图代码解析器
# ============================================================================

class GraphParseError(Exception):
    """解析错误"""
    def __init__(self, message: str, line_number: Optional[int] = None):
        self.message = message
        self.line_number = line_number
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        if self.line_number:
            return f"第{self.line_number}行: {self.message}"
        return self.message


class GraphCodeParser:
    """节点图代码解析器 - 从类结构 Python 文件解析节点图"""
    
    def __init__(self, workspace_path: Path, node_library: Optional[Dict[str, NodeDef]] = None, verbose: bool = False):
        """初始化解析器
        
        Args:
            workspace_path: 工作空间路径（Graph_Generater目录）
            node_library: 可选的节点库（如果为None，则自动加载）
            verbose: 是否输出详细日志
        """
        self.workspace_path = workspace_path
        self.verbose = verbose
        if node_library is not None:
            self.node_library = node_library
        else:
            registry = get_node_registry(workspace_path, include_composite=True)
            self.node_library = registry.get_library()
        self._code_parser = CodeToGraphParser(self.node_library, verbose=self.verbose)
        # 信号定义仓库：用于在 register_handlers 中接受“信号名”或 signal_id，并统一解析为 ID。
        # 使用延迟导入避免在引擎初始化早期引入 `engine.signal` → `engine.validate` → `engine.graph` 的循环依赖。
        self._signal_repo = None
    
    def parse_file(self, code_file: Path) -> Tuple[GraphModel, Dict[str, Any]]:
        """解析节点图代码文件为 GraphModel 和元数据
        
        Args:
            code_file: 文件路径
            
        Returns:
            (GraphModel, metadata字典)
            
        Raises:
            GraphParseError: 解析失败时抛出
        """
        # 文件路径用于错误信息
        file_path_str = str(code_file)
        
        # 1. 读取文件内容
        with open(code_file, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 2. 仅支持类结构格式（虚拟挂载架构）。判定失败直接报错。
        if not is_class_structure_format(code):
            raise GraphParseError(
                f"当前节点图文件不符合类结构 Python 格式。文件: {file_path_str}"
            )
        # 新格式：类结构（虚拟挂载架构）
        return self._parse_class_structure(code, code_file)
    
    def _parse_class_structure(self, code: str, code_file: Path) -> Tuple[GraphModel, Dict[str, Any]]:
        """解析类结构格式的节点图，委托CodeToGraphParser
        
        Args:
            code: 源代码
            code_file: 文件路径
            
        Returns:
            (GraphModel, metadata)
        """
        # 1. 提取元数据
        tree = ast.parse(code)
        metadata_obj = extract_metadata_from_code(code)
        metadata = {
            "graph_id": metadata_obj.graph_id,
            "graph_name": (metadata_obj.graph_name or "未命名节点图"),
            "graph_type": (metadata_obj.graph_type or "server"),
            "folder_path": metadata_obj.folder_path,
            "description": metadata_obj.description,
            "graph_variables": metadata_obj.graph_variables,
            "dynamic_ports": metadata_obj.dynamic_ports,
        }
        
        graph_name = metadata.get("graph_name", "未命名节点图")
        
        # 2. 委托CodeToGraphParser解析
        graph_model = self._code_parser.parse_code(code, graph_name, tree=tree)
        
        # 3. 设置元数据到GraphModel
        graph_model.graph_id = metadata.get("graph_id", graph_model.graph_id)
        graph_model.graph_name = graph_name
        graph_model.description = metadata.get("description", "")
        graph_model.metadata["parsed_from_class_structure"] = True
        graph_model.metadata["graph_type"] = metadata.get("graph_type", "server")
        # 使用相对仓库根目录的路径，避免泄露本地绝对路径
        workspace_root = self.workspace_path.resolve()
        code_path = code_file.resolve()
        root_parts = workspace_root.parts
        path_parts = code_path.parts
        relative_str = ""
        if len(path_parts) >= len(root_parts) and path_parts[:len(root_parts)] == root_parts:
            tail_parts = path_parts[len(root_parts):]
            if tail_parts:
                relative_str = "/".join(tail_parts)
            else:
                relative_str = code_path.name
        else:
            # 不在工作区下时，保存文件名以避免绝对路径
            relative_str = code_path.name
        graph_model.metadata["source_file"] = relative_str
        graph_model.metadata["parsed_at"] = datetime.now().isoformat()
        
        # 4. 语义推导已下沉到 IR 管线：
        # - register_handlers → 【监听信号】绑定由 CodeToGraphParser 在创建事件节点时完成；
        # - 模块/方法内命名常量在 IR 解析阶段直接回填到 node.input_constants；
        # - 结构体节点绑定在节点创建当刻写入 GraphModel.metadata["struct_bindings"]。
        
        # 同步 docstring/代码中的图变量
        if metadata.get("graph_variables"):
            graph_model.graph_variables = metadata["graph_variables"]
        
        # 6. 提取并关联注释
        associate_comments_to_nodes(code, graph_model)
        
        if self.verbose:
            print(f"[OK] 成功解析节点图: {graph_name}")
            print(f"  节点数: {len(graph_model.nodes)}, 连线数: {len(graph_model.edges)}")
        
        return graph_model, metadata
    
    def _apply_constant_bindings_from_code(
        self,
        tree: ast.Module,
        graph_model: GraphModel,
    ) -> None:
        """从 Graph Code 中的常量变量声明推导节点输入常量。

        约定：
        - 支持形如 `变量名: "类型" = <常量>` 或 `变量名 = <常量>` 的简单常量变量；
        - 常量变量仅在作为节点调用参数时生效：不再通过连线提供数据来源，
          而是直接写入对应节点的 `input_constants[端口名]`。
        """
        if not isinstance(tree, ast.Module):
            return

        graph_class = find_graph_class(tree)
        if graph_class is None:
            return

        all_nodes: List[NodeModel] = list(graph_model.nodes.values())
        if not all_nodes:
            return

        # 收集模块顶层的简单常量声明（AnnAssign/Assign，右值为字面量），
        # 例如：地点/配置等命名常量，供事件方法体内引用时回填到节点输入常量。
        global_const_values: Dict[str, str] = {}
        for top_stmt in tree.body:
            if isinstance(top_stmt, ast.AnnAssign):
                target = getattr(top_stmt, "target", None)
                value = getattr(top_stmt, "value", None)
                if isinstance(target, ast.Name) and isinstance(value, ast.Constant):
                    name_text = target.id.strip()
                    if name_text != "":
                        global_const_values[name_text] = str(value.value)
            elif isinstance(top_stmt, ast.Assign):
                targets = list(getattr(top_stmt, "targets", []) or [])
                value = getattr(top_stmt, "value", None)
                if len(targets) == 1 and isinstance(targets[0], ast.Name) and isinstance(value, ast.Constant):
                    name_text = targets[0].id.strip()
                    if name_text != "":
                        global_const_values[name_text] = str(value.value)

        node_library = self.node_library
        node_name_index = getattr(self._code_parser, "node_name_index", None)
        if node_name_index is None:
            from engine.graph.common import node_name_index_from_library

            node_name_index = node_name_index_from_library(node_library)

        for item in graph_class.body:
            if not isinstance(item, ast.FunctionDef):
                continue
            if not item.name.startswith("on_"):
                continue

            stmts: List[ast.stmt] = list(item.body or [])
            if not stmts:
                continue

            method_lineno = getattr(item, "lineno", 0) or 0
            method_end_lineno = getattr(item, "end_lineno", method_lineno) or method_lineno
            if not isinstance(method_lineno, int) or method_lineno <= 0:
                continue
            if not isinstance(method_end_lineno, int) or method_end_lineno < method_lineno:
                method_end_lineno = method_lineno

            method_nodes: List[NodeModel] = []
            for node in all_nodes:
                node_start = getattr(node, "source_lineno", 0) or 0
                node_end = getattr(node, "source_end_lineno", node_start) or node_start
                if not isinstance(node_start, int) or node_start <= 0:
                    continue
                if not isinstance(node_end, int) or node_end < node_start:
                    node_end = node_start
                if node_end < method_lineno or node_start > method_end_lineno:
                    continue
                method_nodes.append(node)

            if not method_nodes:
                continue

            tracker = ParamUsageTracker(
                param_names=[],
                node_name_index=node_name_index,
                node_library=node_library,
                verbose=self.verbose,
                state_attr_to_param=None,
            )

            # 预填充模块级命名常量，使其在调用参数中可被视为常量变量。
            if global_const_values:
                for var_name, const_val in global_const_values.items():
                    if var_name not in tracker.const_var_values:
                        tracker.const_var_values[var_name] = const_val

            tracker.collect_constants(stmts)
            if not tracker.const_var_values:
                continue

            tracker.backfill_constants_to_nodes(stmts, method_nodes)

    def _apply_signal_bindings_from_register_handlers(
        self,
        tree: ast.Module,
        graph_model: GraphModel,
    ) -> None:
        """已弃用：GraphCodeParser 不再直接写入语义元数据。

        说明：
        - 历史上该方法会在解析阶段写入 `metadata["signal_bindings"]`；
        - 现在信号绑定统一由 `engine.graph.semantic.GraphSemanticPass` 覆盖式生成。
        """
        _ = (tree, graph_model)
        return

    def _resolve_signal_id_from_literal(self, literal: str) -> str:
        """已弃用：仅保留签名以避免旧代码导入时报错。"""
        return str(literal or "").strip()

    def _apply_struct_bindings_from_code(
        self,
        tree: ast.Module,
        graph_model: GraphModel,
    ) -> None:
        """已弃用：GraphCodeParser 不再直接写入语义元数据。

        说明：
        - 历史上该方法会在解析阶段写入 `metadata["struct_bindings"]`；
        - 现在结构体绑定统一由 `engine.graph.semantic.GraphSemanticPass` 覆盖式生成。
        """
        _ = (tree, graph_model)
        return
