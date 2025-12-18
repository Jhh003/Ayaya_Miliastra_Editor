from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from engine.configs.resource_types import ResourceType
from engine.graph.composite_code_parser import CompositeCodeParser
from engine.nodes.composite_file_policy import discover_composite_definition_files, is_composite_definition_file
from engine.nodes.node_registry import get_node_registry
from engine.validate import collect_composite_structural_issues, validate_files
from engine.validate.comprehensive_types import ValidationIssue
from engine.validate.issue import EngineIssue


@dataclass(frozen=True)
class GraphCodeValidationOptions:
    scope: str  # "package" | "all"
    strict_entity_wire_only: bool = False
    disable_cache: bool = False
    enable_composite_struct_check: bool = True


def _normalize_slash(text: str) -> str:
    return text.replace("\\", "/")


def _relative_path_for_display(path: Path, workspace: Path) -> str:
    resolved_path = path.resolve()
    resolved_workspace = workspace.resolve()
    resolved_path_text = _normalize_slash(str(resolved_path))
    resolved_workspace_text = _normalize_slash(str(resolved_workspace))
    prefix = resolved_workspace_text + "/"
    if resolved_path_text.startswith(prefix):
        return resolved_path_text[len(prefix) :]
    return resolved_path_text


def _split_message_and_suggestion(message: str) -> Tuple[str, str]:
    marker = "\n建议："
    if marker not in message:
        return message, ""
    head, tail = message.split(marker, 1)
    return head.strip(), tail.strip()


class GraphCodeValidationService:
    """节点图源码/复合节点源码校验服务：为 UI 生成可展示与可跳转的 ValidationIssue 列表。"""

    def validate_for_ui(
        self,
        *,
        resource_manager: Any,
        current_package: Optional[Any],
        options: GraphCodeValidationOptions,
    ) -> List[ValidationIssue]:
        workspace_path = Path(getattr(resource_manager, "workspace_path", Path(".")))

        targets = self._collect_targets(
            resource_manager=resource_manager,
            current_package=current_package,
            options=options,
            workspace_path=workspace_path,
        )
        if not targets:
            return []

        report = validate_files(
            targets,
            workspace_path,
            strict_entity_wire_only=bool(options.strict_entity_wire_only),
            use_cache=not bool(options.disable_cache),
        )
        engine_issues: List[EngineIssue] = list(report.issues)
        if bool(options.enable_composite_struct_check):
            engine_issues.extend(collect_composite_structural_issues(targets, workspace_path))

        file_context = self._build_file_context(
            resource_manager=resource_manager,
            current_package=current_package,
            options=options,
            targets=targets,
            workspace_path=workspace_path,
            engine_issues=engine_issues,
        )
        return self._convert_engine_issues_to_validation(
            engine_issues,
            workspace_path=workspace_path,
            file_context=file_context,
        )

    def _collect_targets(
        self,
        *,
        resource_manager: Any,
        current_package: Optional[Any],
        options: GraphCodeValidationOptions,
        workspace_path: Path,
    ) -> List[Path]:
        scope = str(options.scope or "")
        if scope not in ("package", "all"):
            raise ValueError(f"未知的 GraphCodeValidationOptions.scope: {scope!r}")

        targets: List[Path] = []
        if scope == "all":
            targets.extend(self._collect_all_graph_files(workspace_path))
        else:
            targets.extend(
                self._collect_package_graph_files(
                    resource_manager=resource_manager,
                    current_package=current_package,
                )
            )

        # 复合节点定义文件：始终纳入（复合节点是全局资源，且节点图常会依赖）
        targets.extend(discover_composite_definition_files(workspace_path))
        return self._deduplicate_preserve_order(targets)

    def _collect_all_graph_files(self, workspace_path: Path) -> List[Path]:
        graphs_dir = workspace_path / "assets" / "资源库" / "节点图"
        if not graphs_dir.exists():
            return []
        collected: List[Path] = []
        for path in sorted(graphs_dir.rglob("*.py")):
            if path.name.startswith("_"):
                continue
            if "校验" in path.stem:
                continue
            collected.append(path)
        return collected

    def _collect_package_graph_files(
        self,
        *,
        resource_manager: Any,
        current_package: Optional[Any],
    ) -> List[Path]:
        if current_package is None:
            return []

        graph_ids: List[str] = []
        graph_id_set: set[str] = set()

        package_index = getattr(current_package, "package_index", None)
        package_resources = getattr(package_index, "resources", None) if package_index is not None else None
        declared_graph_ids = list(getattr(package_resources, "graphs", []) or [])
        for graph_id in declared_graph_ids:
            graph_id_text = str(graph_id or "")
            if graph_id_text and graph_id_text not in graph_id_set:
                graph_id_set.add(graph_id_text)
                graph_ids.append(graph_id_text)

        templates = getattr(current_package, "templates", {}) or {}
        for template in templates.values():
            for graph_id in list(getattr(template, "default_graphs", []) or []):
                graph_id_text = str(graph_id or "")
                if graph_id_text and graph_id_text not in graph_id_set:
                    graph_id_set.add(graph_id_text)
                    graph_ids.append(graph_id_text)

        instances = getattr(current_package, "instances", {}) or {}
        for instance in instances.values():
            for graph_id in list(getattr(instance, "additional_graphs", []) or []):
                graph_id_text = str(graph_id or "")
                if graph_id_text and graph_id_text not in graph_id_set:
                    graph_id_set.add(graph_id_text)
                    graph_ids.append(graph_id_text)

        level_entity = getattr(current_package, "level_entity", None)
        additional_graphs = list(getattr(level_entity, "additional_graphs", []) or []) if level_entity else []
        for graph_id in additional_graphs:
            graph_id_text = str(graph_id or "")
            if graph_id_text and graph_id_text not in graph_id_set:
                graph_id_set.add(graph_id_text)
                graph_ids.append(graph_id_text)

        target_files: List[Path] = []
        get_graph_file_path = getattr(resource_manager, "get_graph_file_path", None)
        if not callable(get_graph_file_path):
            return []
        for graph_id in graph_ids:
            file_path = get_graph_file_path(graph_id)
            if isinstance(file_path, Path) and file_path.is_file():
                target_files.append(file_path)
        return target_files

    @staticmethod
    def _deduplicate_preserve_order(paths: Sequence[Path]) -> List[Path]:
        seen: set[str] = set()
        unique: List[Path] = []
        for path in paths:
            resolved_text = str(path.resolve())
            if resolved_text in seen:
                continue
            seen.add(resolved_text)
            unique.append(path)
        return unique

    def _build_file_context(
        self,
        *,
        resource_manager: Any,
        current_package: Optional[Any],
        options: GraphCodeValidationOptions,
        targets: List[Path],
        workspace_path: Path,
        engine_issues: List[EngineIssue],
    ) -> Dict[str, Dict[str, object]]:
        """构建：绝对文件路径 -> UI 跳转上下文(detail) 的映射。"""
        _ = options
        file_context: Dict[str, Dict[str, object]] = {}

        # 1) Graph 文件：尝试绑定 graph_id，并在“当前存档”范围下尽量绑定 owner（template/instance/level_entity）
        graph_id_by_abs_path: Dict[str, str] = {}
        list_resources = getattr(resource_manager, "list_resources", None)
        get_graph_file_path = getattr(resource_manager, "get_graph_file_path", None)
        if callable(list_resources) and callable(get_graph_file_path):
            graph_ids_all = list(list_resources(ResourceType.GRAPH) or [])
            for graph_id_value in graph_ids_all:
                graph_id = str(graph_id_value or "")
                if not graph_id:
                    continue
                file_path = get_graph_file_path(graph_id)
                if isinstance(file_path, Path) and file_path.is_file():
                    graph_id_by_abs_path[str(file_path.resolve())] = graph_id

        graph_owner_by_id: Dict[str, Dict[str, object]] = {}
        if current_package is not None:
            # 优先级：实例 > 模板 > 关卡实体（越具体越优先）
            instances = getattr(current_package, "instances", {}) or {}
            for instance_id, instance in instances.items():
                for graph_id_value in list(getattr(instance, "additional_graphs", []) or []):
                    graph_id = str(graph_id_value or "")
                    if graph_id:
                        graph_owner_by_id.setdefault(
                            graph_id,
                            {"type": "instance", "instance_id": str(instance_id or "")},
                        )

            templates = getattr(current_package, "templates", {}) or {}
            for template_id, template in templates.items():
                for graph_id_value in list(getattr(template, "default_graphs", []) or []):
                    graph_id = str(graph_id_value or "")
                    if graph_id:
                        graph_owner_by_id.setdefault(
                            graph_id,
                            {"type": "template", "template_id": str(template_id or "")},
                        )

            level_entity = getattr(current_package, "level_entity", None)
            additional_graphs = (
                list(getattr(level_entity, "additional_graphs", []) or []) if level_entity else []
            )
            for graph_id_value in additional_graphs:
                graph_id = str(graph_id_value or "")
                if graph_id:
                    graph_owner_by_id.setdefault(graph_id, {"type": "level_entity"})

        for target_path in targets:
            abs_text = str(target_path.resolve())
            graph_id = graph_id_by_abs_path.get(abs_text)
            if not graph_id:
                continue
            owner_detail = graph_owner_by_id.get(graph_id) or {"type": "graph"}
            file_context[abs_text] = {
                **dict(owner_detail),
                "graph_id": graph_id,
            }

        # 2) Composite 文件：仅对“实际出现 issue 的复合文件”解析一次，补齐 composite_id/node_name 以便跳转
        composite_issue_files: set[str] = set()
        for issue in engine_issues:
            abs_path = self._resolve_issue_file_to_abs(issue, workspace_path=workspace_path)
            if not abs_path:
                continue
            if is_composite_definition_file(Path(abs_path)):
                composite_issue_files.add(abs_path)

        if composite_issue_files:
            registry = get_node_registry(workspace_path, include_composite=True)
            node_library = registry.get_library()
            parser = CompositeCodeParser(node_library, verbose=False, workspace_path=workspace_path)
            for abs_path in sorted(composite_issue_files):
                composite = parser.parse_file(Path(abs_path))
                file_context.setdefault(
                    abs_path,
                    {
                        "type": "composite_node",
                        "composite_id": str(getattr(composite, "composite_id", "") or ""),
                        "node_name": str(getattr(composite, "node_name", "") or ""),
                    },
                )

        return file_context

    @staticmethod
    def _resolve_issue_file_to_abs(issue: EngineIssue, *, workspace_path: Path) -> str:
        file_value = getattr(issue, "file", None)
        if not isinstance(file_value, str) or not file_value:
            return ""
        if file_value.startswith("<"):
            return ""
        raw_path = Path(file_value)
        absolute_path = raw_path if raw_path.is_absolute() else (workspace_path / raw_path)
        return str(absolute_path.resolve())

    def _convert_engine_issues_to_validation(
        self,
        engine_issues: List[EngineIssue],
        *,
        workspace_path: Path,
        file_context: Dict[str, Dict[str, object]],
    ) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        for issue in engine_issues:
            absolute_file_path = self._resolve_issue_file_to_abs(issue, workspace_path=workspace_path)
            relative_file_text = ""
            if absolute_file_path:
                relative_file_text = _relative_path_for_display(Path(absolute_file_path), workspace_path)

            location_text = str(getattr(issue, "location", None) or "")
            if not location_text:
                line_span = getattr(issue, "line_span", None)
                if isinstance(line_span, str) and line_span:
                    location_text = f"{relative_file_text}:{line_span}" if relative_file_text else f"(未知文件):{line_span}"
                else:
                    location_text = relative_file_text or "（无具体位置）"

            base_detail: Dict[str, object] = {}
            raw_detail = getattr(issue, "detail", None)
            if isinstance(raw_detail, dict):
                base_detail = dict(raw_detail)

            # 注入：来源与文件上下文（用于 UI 跳转）
            base_detail.setdefault("validation_source", "graph_code")
            if absolute_file_path:
                base_detail.setdefault("file", relative_file_text or str(getattr(issue, "file", "") or ""))

            context_detail = file_context.get(absolute_file_path, {})
            if isinstance(context_detail, dict) and context_detail:
                # 优先使用 context 的 type（template/instance/level_entity/composite_node/...）
                if "type" in context_detail and "type" not in base_detail:
                    base_detail["type"] = context_detail.get("type")
                for key, value in context_detail.items():
                    if key == "type":
                        continue
                    base_detail.setdefault(key, value)

            # 若仍无 type 但能解析出 graph_id，则给一个可跳转的默认 type
            if "type" not in base_detail and "graph_id" in base_detail:
                base_detail["type"] = "graph"

            message_text = str(getattr(issue, "message", "") or "")
            message_text, suggestion_text = _split_message_and_suggestion(message_text)

            issues.append(
                ValidationIssue(
                    level=str(getattr(issue, "level", "") or ""),
                    category=str(getattr(issue, "category", "") or ""),
                    code=str(getattr(issue, "code", "") or ""),
                    message=message_text,
                    file=relative_file_text or str(getattr(issue, "file", "") or ""),
                    graph_id=getattr(issue, "graph_id", None),
                    location=location_text,
                    node_id=getattr(issue, "node_id", None),
                    port=getattr(issue, "port", None),
                    line_span=getattr(issue, "line_span", None),
                    suggestion=suggestion_text,
                    reference=str(getattr(issue, "reference", "") or ""),
                    detail=base_detail,
                )
            )

        return issues


__all__ = ["GraphCodeValidationOptions", "GraphCodeValidationService"]


