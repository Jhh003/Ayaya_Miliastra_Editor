from __future__ import annotations

from engine.graph.models.graph_model import GraphModel
from engine.resources.resource_manager import ResourceManager


class GraphEditorValidateService:
    """节点图验证流程服务：生成 UI 可用 issues 列表（不发射 UI 信号）。"""

    def validate_for_ui(
        self,
        *,
        model: GraphModel,
        resource_manager: ResourceManager,
        current_package: object,
        current_container: object,
        object_type: str,
        graph_id: str,
    ) -> list:
        entity_type = self._infer_entity_type(
            current_package=current_package,
            current_container=current_container,
            object_type=str(object_type or ""),
        )

        container_name = getattr(current_container, "name", "") or "当前对象"
        location = f"{container_name} > 节点图 '{graph_id}'"
        detail = {"type": object_type, "graph_name": graph_id}

        from engine.validate.comprehensive_validator import ComprehensiveValidator

        validator = ComprehensiveValidator(current_package, resource_manager, verbose=False)
        validator.issues = []
        validator.validate_graph_for_ui(model, entity_type, location, detail)
        return list(validator.issues)

    def _infer_entity_type(self, *, current_package: object, current_container: object, object_type: str) -> str:
        if object_type == "level_entity":
            return "关卡"

        if object_type == "template":
            return getattr(current_container, "entity_type", "") or "未知"

        if object_type == "instance":
            template_id = getattr(current_container, "template_id", None)
            get_template = getattr(current_package, "get_template", None)
            if callable(get_template) and template_id:
                template = get_template(template_id)
                return getattr(template, "entity_type", "") or "未知"
            return "未知"

        return "未知"


