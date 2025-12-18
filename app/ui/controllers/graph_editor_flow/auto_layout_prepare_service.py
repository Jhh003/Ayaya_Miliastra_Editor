from __future__ import annotations

from dataclasses import dataclass

from engine.graph.models.graph_model import GraphModel
from engine.resources.resource_manager import ResourceManager, ResourceType


@dataclass(frozen=True, slots=True)
class GraphReparseResult:
    graph_data: dict | None


class GraphEditorAutoLayoutPrepareService:
    """自动排版前准备流程服务（不发射 UI 信号）。"""

    def reparse_graph_from_py(self, *, resource_manager: ResourceManager, graph_id: str) -> GraphReparseResult:
        resource_manager.invalidate_graph_for_reparse(str(graph_id))
        fresh = resource_manager.load_resource(ResourceType.GRAPH, str(graph_id))
        if not isinstance(fresh, dict):
            return GraphReparseResult(graph_data=None)
        graph_data = fresh.get("data") or {}
        if not isinstance(graph_data, dict) or not graph_data:
            return GraphReparseResult(graph_data=None)
        return GraphReparseResult(graph_data=graph_data)

    def build_persistent_cache_payload(self, *, graph_id: str, model: GraphModel) -> dict:
        graph_data = model.serialize()
        return {
            "graph_id": str(graph_id),
            "name": graph_data.get("graph_name", str(graph_id)),
            "graph_type": graph_data.get("metadata", {}).get("graph_type", "server"),
            "folder_path": graph_data.get("metadata", {}).get("folder_path", ""),
            "description": graph_data.get("description", ""),
            "data": graph_data,
            "metadata": {},
        }


