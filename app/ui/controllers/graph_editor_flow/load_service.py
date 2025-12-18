from __future__ import annotations

from dataclasses import dataclass

from PyQt6 import QtWidgets

from app.models.edit_session_capabilities import EditSessionCapabilities
from app.ui.graph.graph_scene import GraphScene
from app.ui.graph.graph_view import GraphView
from app.ui.graph.scene_builder import populate_scene_from_model
from engine.graph.common import (
    SIGNAL_LISTEN_NODE_TITLE,
    SIGNAL_LISTEN_STATIC_OUTPUTS,
    SIGNAL_SEND_NODE_TITLE,
    SIGNAL_SEND_STATIC_INPUTS,
)
from engine.graph.models.graph_model import GraphModel
from engine.graph.semantic import GraphSemanticPass
from engine.signal import compute_signal_schema_hash


@dataclass(frozen=True, slots=True)
class GraphEditorLoadRequest:
    graph_id: str
    graph_data: dict
    container: object | None
    scene_extra_options_override: dict | None = None


@dataclass(frozen=True, slots=True)
class GraphEditorLoadResult:
    graph_id: str
    model: GraphModel
    scene: GraphScene
    container: object | None
    baseline_content_hash: str


class GraphEditorLoadService:
    """节点图加载管线服务（不发射 UI 信号）。"""

    def load(
        self,
        *,
        request: GraphEditorLoadRequest,
        current_scene: GraphScene,
        view: GraphView,
        node_library: dict,
        edit_session_capabilities: EditSessionCapabilities,
        base_scene_extra_options: dict,
        get_current_package: object,
        main_window: object,
        on_graph_modified: object,
    ) -> GraphEditorLoadResult:
        graph_id = str(request.graph_id)
        graph_data = request.graph_data

        if not isinstance(graph_data, dict) or not graph_data:
            raise ValueError("节点图数据为空或类型错误")

        # 清空旧场景以释放图元；随后会替换为新 GraphScene。
        current_scene.clear()

        model = GraphModel.deserialize(graph_data)
        self._sync_composite_nodes_from_library_if_needed(model=model, node_library=node_library)
        # 语义元数据（signal_bindings/struct_bindings）统一由 GraphSemanticPass 覆盖式生成，
        # 在 UI 加载阶段做一次对齐，避免旧数据/多源写入残留导致的不确定行为。
        GraphSemanticPass.apply(model=model)

        scene_options = self._build_scene_options_for_load(
            base_scene_extra_options=base_scene_extra_options,
            scene_extra_options_override=request.scene_extra_options_override,
            get_current_package=get_current_package,
            main_window=main_window,
        )

        new_scene = GraphScene(
            model,
            read_only=bool(edit_session_capabilities.is_read_only),
            node_library=node_library,
            edit_session_capabilities=edit_session_capabilities,
            **scene_options,
        )

        # 绑定修改回调（自动保存/脏标记入口）
        new_scene.undo_manager.on_change_callback = on_graph_modified  # type: ignore[assignment]
        new_scene.on_data_changed = on_graph_modified  # type: ignore[assignment]

        # 替换视图场景并同步 node_library（菜单/过滤等依赖）
        view.setScene(new_scene)
        view.node_library = node_library

        scope = (model.metadata or {}).get("graph_type", "server")
        if scope in ("server", "client"):
            view.current_scope = scope

        self._populate_scene_with_batch_settings(
            scene=new_scene,
            view=view,
            get_current_package=get_current_package,
        )

        baseline_hash = model.get_content_hash()
        return GraphEditorLoadResult(
            graph_id=graph_id,
            model=model,
            scene=new_scene,
            container=request.container,
            baseline_content_hash=baseline_hash,
        )

    def _build_scene_options_for_load(
        self,
        *,
        base_scene_extra_options: dict,
        scene_extra_options_override: dict | None,
        get_current_package: object,
        main_window: object,
    ) -> dict:
        signal_edit_context = {"get_current_package": get_current_package, "main_window": main_window}
        scene_options = dict(base_scene_extra_options or {})
        if scene_extra_options_override:
            scene_options.update(scene_extra_options_override)
        scene_options["signal_edit_context"] = signal_edit_context
        return scene_options

    def _sync_composite_nodes_from_library_if_needed(self, *, model: GraphModel, node_library: dict) -> None:
        if not isinstance(node_library, dict) or not node_library:
            return
        updated_count = model.sync_composite_nodes_from_library(node_library)
        if updated_count > 0:
            print(f"[加载] 同步了 {updated_count} 个复合节点的端口定义")

    def _populate_scene_with_batch_settings(self, *, scene: GraphScene, view: GraphView, get_current_package: object) -> None:
        view.setUpdatesEnabled(False)
        old_on_change_cb = scene.undo_manager.on_change_callback
        old_on_data_changed = scene.on_data_changed
        scene.undo_manager.on_change_callback = None
        scene.on_data_changed = None
        scene.setItemIndexMethod(QtWidgets.QGraphicsScene.ItemIndexMethod.NoIndex)

        populate_scene_from_model(scene, enable_batch_mode=True)

        if hasattr(scene, "_on_signals_updated_from_manager"):
            self._maybe_sync_signals_for_model(scene=scene, model=scene.model, get_current_package=get_current_package)

        scene.setItemIndexMethod(QtWidgets.QGraphicsScene.ItemIndexMethod.BspTreeIndex)
        scene.undo_manager.on_change_callback = old_on_change_cb
        scene.on_data_changed = old_on_data_changed
        view.setUpdatesEnabled(True)
        view.viewport().update()

        self._refresh_mini_map_after_batch_build(view=view)

    def _refresh_mini_map_after_batch_build(self, *, view: GraphView) -> None:
        if hasattr(view, "mini_map") and view.mini_map:
            from app.ui.graph.graph_view.assembly.view_assembly import ViewAssembly

            ViewAssembly.update_mini_map_position(view)
            view.mini_map.show()
            view.mini_map.raise_()

    def _maybe_sync_signals_for_model(self, *, scene: GraphScene, model: GraphModel, get_current_package: object) -> None:
        get_current_package_callable = get_current_package if callable(get_current_package) else None
        if get_current_package_callable is None:
            scene._on_signals_updated_from_manager()  # type: ignore[call-arg]
            return

        current_package = get_current_package_callable()
        if current_package is None:
            scene._on_signals_updated_from_manager()  # type: ignore[call-arg]
            return

        signals_dict = getattr(current_package, "signals", None)
        if not isinstance(signals_dict, dict):
            scene._on_signals_updated_from_manager()  # type: ignore[call-arg]
            return

        current_hash = compute_signal_schema_hash(signals_dict)
        metadata = model.metadata or {}
        last_hash_value = metadata.get("signal_schema_hash")

        need_force_resync: bool = False
        if isinstance(last_hash_value, str) and last_hash_value == current_hash:
            bindings = model.get_signal_bindings()

            for node_id, node in model.nodes.items():
                node_title = getattr(node, "title", "") or ""
                if node_title not in (SIGNAL_SEND_NODE_TITLE, SIGNAL_LISTEN_NODE_TITLE):
                    continue

                binding_info = bindings.get(str(node_id)) or {}
                signal_id_value = binding_info.get("signal_id")
                if not isinstance(signal_id_value, str) or not signal_id_value:
                    continue

                signal_config = signals_dict.get(signal_id_value)
                if signal_config is None:
                    continue

                parameters = getattr(signal_config, "parameters", []) or []
                param_names: list[str] = []
                for param in parameters:
                    name_value = getattr(param, "name", "")
                    if isinstance(name_value, str) and name_value:
                        param_names.append(name_value)
                if not param_names:
                    continue

                if node_title == SIGNAL_SEND_NODE_TITLE:
                    static_ports = set(SIGNAL_SEND_STATIC_INPUTS)
                    existing_names = {
                        str(getattr(port, "name", ""))
                        for port in (getattr(node, "inputs", []) or [])
                        if hasattr(port, "name")
                    }
                else:
                    static_ports = set(SIGNAL_LISTEN_STATIC_OUTPUTS)
                    existing_names = {
                        str(getattr(port, "name", ""))
                        for port in (getattr(node, "outputs", []) or [])
                        if hasattr(port, "name")
                    }

                for param_name in param_names:
                    if param_name in static_ports:
                        continue
                    if param_name not in existing_names:
                        need_force_resync = True
                        break
                if need_force_resync:
                    break

            if not need_force_resync:
                return

        scene._on_signals_updated_from_manager()  # type: ignore[call-arg]
        metadata["signal_schema_hash"] = current_hash
        model.metadata = metadata


