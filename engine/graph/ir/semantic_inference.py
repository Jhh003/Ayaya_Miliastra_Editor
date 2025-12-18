from __future__ import annotations

import ast
from typing import List, Optional

from engine.graph.models import GraphModel, NodeModel
from .node_factory import FactoryContext


def apply_call_semantics(
    *,
    node: NodeModel,
    call_expr: ast.Call,
    graph_model: GraphModel,
    ctx: FactoryContext,
    assigned_names: Optional[List[str]] = None,
) -> None:
    """已弃用：IR 层不再写入语义元数据。

    历史上本函数会在 IR 构造节点时直接写入：
    - `GraphModel.metadata["signal_bindings"]`
    - `GraphModel.metadata["struct_bindings"]`

    这会导致 Parser/IR/UI 多源写入、覆盖规则不清晰的问题。

    现在语义元数据统一由 `engine.graph.semantic.GraphSemanticPass` 在明确阶段覆盖式生成，
    本函数仅保留签名以避免旧代码导入时报错，不再进行任何写入。
    """

    _ = (node, call_expr, graph_model, ctx, assigned_names)
    return


__all__ = ["apply_call_semantics"]


