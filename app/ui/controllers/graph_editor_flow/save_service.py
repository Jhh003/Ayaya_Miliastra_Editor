from __future__ import annotations

from dataclasses import dataclass

from engine.resources.resource_manager import ResourceManager, ResourceType
from engine.graph.models.graph_model import GraphModel


@dataclass(frozen=True, slots=True)
class GraphEditorSaveResult:
    success: bool
    error_message: str | None = None
    error_code: str | None = None


class GraphEditorSaveService:
    """节点图保存流程服务（不发射 UI 信号）。"""

    def save_graph(self, *, resource_manager: ResourceManager, graph_id: str, model: GraphModel) -> GraphEditorSaveResult:
        current_graph_data = model.serialize()

        if not current_graph_data.get("graph_id") or not current_graph_data.get("graph_name"):
            return GraphEditorSaveResult(
                success=False,
                error_code="incomplete_data",
                error_message=(
                    "节点图数据不完整，取消保存："
                    f"graph_id={current_graph_data.get('graph_id')}, graph_name={current_graph_data.get('graph_name')}"
                ),
            )

        save_ok = resource_manager.save_resource(ResourceType.GRAPH, str(graph_id), current_graph_data)
        if not save_ok:
            return GraphEditorSaveResult(
                success=False,
                error_code="validation_failed",
                error_message=f"节点图 '{current_graph_data.get('graph_name', graph_id)}' 无法通过验证，保存已取消。",
            )

        saved_data = resource_manager.load_resource(ResourceType.GRAPH, str(graph_id))
        if not saved_data:
            return GraphEditorSaveResult(
                success=False,
                error_code="file_system_error",
                error_message="节点图保存后无法重新加载（文件系统错误）",
            )

        return GraphEditorSaveResult(success=True)


