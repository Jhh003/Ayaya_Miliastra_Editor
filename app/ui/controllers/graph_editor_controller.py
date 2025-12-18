"""节点图编辑控制器 - 管理节点图的编辑逻辑

治理约束（重要）：
- 本文件仅负责：依赖注入、Qt 信号转发、调用流程服务；
- 跨域链路（load/save/validate/auto_layout_prepare）下沉到 `app.ui.controllers.graph_editor_flow`；
- 会话能力/只读语义/保存状态统一由状态机收敛为单一真源，避免分叉。
"""

from __future__ import annotations

from typing import Optional

from PyQt6 import QtCore

from engine.graph.models.graph_model import GraphModel
from engine.graph.models.graph_config import GraphConfig
from engine.layout import LayoutService
from engine.resources.resource_manager import ResourceManager
from app.ui.graph.graph_undo import AddNodeCommand
from engine.nodes.node_definition_loader import NodeDef
from app.ui.graph.graph_scene import GraphScene
from app.ui.graph.graph_view import GraphView
from app.ui.controllers.graph_error_tracker import get_instance as get_error_tracker
from app.models.edit_session_capabilities import EditSessionCapabilities
from app.ui.controllers.graph_editor_flow import (
    GraphEditorAutoLayoutPrepareService,
    GraphEditorLoadRequest,
    GraphEditorLoadService,
    GraphEditorSaveService,
    GraphEditorSessionStateMachine,
    GraphEditorValidateService,
    derive_initial_input_names_for_new_node,
)


class GraphEditorController(QtCore.QObject):
    """节点图编辑管理控制器"""
    
    # 信号定义
    graph_loaded = QtCore.pyqtSignal(str)  # graph_id
    graph_saved = QtCore.pyqtSignal(str)  # graph_id
    graph_runtime_cache_updated = QtCore.pyqtSignal(str)  # graph_id（持久化缓存更新/强制重解析等）
    graph_validated = QtCore.pyqtSignal(list)  # issues
    validation_triggered = QtCore.pyqtSignal()
    switch_to_editor_requested = QtCore.pyqtSignal()  # 切换到编辑页面
    title_update_requested = QtCore.pyqtSignal(str)  # 更新窗口标题
    save_status_changed = QtCore.pyqtSignal(str)  # "saved" | "unsaved" | "saving" | "readonly"
    
    def __init__(
        self,
        resource_manager: ResourceManager,
        model: GraphModel,
        scene: GraphScene,
        view: GraphView,
        node_library: dict,
        *,
        edit_session_capabilities: EditSessionCapabilities | None = None,
        parent: Optional[QtCore.QObject] = None
    ):
        super().__init__(parent)
        
        self.resource_manager = resource_manager
        self.model = model
        self.scene = scene
        self.view = view
        self.node_library = node_library
        self._load_service = GraphEditorLoadService()
        self._save_service = GraphEditorSaveService()
        self._validate_service = GraphEditorValidateService()
        self._auto_layout_prepare_service = GraphEditorAutoLayoutPrepareService()
        # 额外场景参数（例如复合节点编辑上下文）
        self._scene_extra_options: dict = {}
        
        # 当前节点图状态（graph_id 由状态机持有，controller 只保留 container）
        self.current_graph_container = None  # 存储当前编辑的对象（template或instance）
        initial_capabilities: EditSessionCapabilities = (
            edit_session_capabilities
            if isinstance(edit_session_capabilities, EditSessionCapabilities)
            else EditSessionCapabilities.interactive_preview()
        )
        self._session_state_machine = GraphEditorSessionStateMachine(capabilities=initial_capabilities)
        
        # 用于获取存档（由主窗口设置）
        self.get_current_package = None
        self.get_property_panel_object_type = None
        
        # 错误跟踪器（单例）
        self.error_tracker = get_error_tracker()
        # 自动保存防抖计时器（根据全局设置控制）
        self._save_debounce_timer: Optional[QtCore.QTimer] = None
        # 下次自动排版前是否强制从 .py 重新解析（忽略持久化缓存）
        self._force_reparse_on_next_auto_layout: bool = False

        # 启动时同步一次能力到初始 scene/view，避免出现“控制器能力已设定但 view/scene 仍沿用旧状态”。
        self._apply_edit_session_capabilities_to_view_and_scene()

    # === EditSessionCapabilities + save_status（单一真源：状态机） ===

    @property
    def edit_session_capabilities(self) -> EditSessionCapabilities:
        return self._session_state_machine.capabilities

    def set_edit_session_capabilities(self, capabilities: EditSessionCapabilities) -> None:
        current_hash = self.model.get_content_hash() if self.model is not None else None
        new_status = self._session_state_machine.set_capabilities(capabilities, current_content_hash=current_hash)
        self._apply_edit_session_capabilities_to_view_and_scene()
        self.save_status_changed.emit(new_status)

    def _apply_edit_session_capabilities_to_view_and_scene(self) -> None:
        capabilities = self._session_state_machine.capabilities
        if self.view is not None and hasattr(self.view, "set_edit_session_capabilities"):
            self.view.set_edit_session_capabilities(capabilities)
        if self.scene is not None and hasattr(self.scene, "set_edit_session_capabilities"):
            self.scene.set_edit_session_capabilities(capabilities)

        if self.view is not None:
            # “添加节点”入口仅在可交互会话开放
            self.view.on_add_node_callback = (
                self.add_node_at_position if capabilities.can_interact else None
            )

    # === 兼容字段：logic_read_only（历史语义） ===

    @property
    def logic_read_only(self) -> bool:
        """历史字段：映射为“不可保存到资源落盘”。"""
        return not self._session_state_machine.capabilities.can_persist

    @logic_read_only.setter
    def logic_read_only(self, value: bool) -> None:
        # 兼容旧写法：只改“可保存”能力位；可保存要求可校验，交由 EditSessionCapabilities 自身约束。
        self.set_edit_session_capabilities(
            self._session_state_machine.capabilities.with_overrides(can_persist=not bool(value))
        )

    @property
    def current_graph_id(self) -> Optional[str]:
        """当前图 id：由状态机持有，避免与 save_status/baseline 分叉。"""
        return self._session_state_machine.current_graph_id

    @current_graph_id.setter
    def current_graph_id(self, value: Optional[str]) -> None:
        # 兼容旧代码：允许外部清空 current_graph_id（例如缓存清理回退逻辑）。
        if value is None:
            self._session_state_machine.on_graph_closed()
            return
        self._session_state_machine.current_graph_id = str(value)

    def schedule_reparse_on_next_auto_layout(self) -> None:
        """安排在下一次自动排版前强制从 .py 重新解析当前图（忽略持久化缓存）。"""
        self._force_reparse_on_next_auto_layout = True

    def prepare_for_auto_layout(self) -> None:
        """在自动排版前按需（一次性标记）重建模型：清缓存→从 .py 解析→替换到场景。
        
        说明：
        - 默认不重载，避免打断当前视图缩放/中心导致“居中偏移”的体验问题。
        - 当设置页面触发一次性标记（例如 DATA_NODE_CROSS_BLOCK_COPY 从 True→False）时，
          才进行清缓存与重载；重载前后会保存并恢复视图缩放与中心点，保持画面稳定。
        """
        if not self.current_graph_id:
            self._force_reparse_on_next_auto_layout = False
            return

        graph_id = str(self.current_graph_id)
        
        # 仅当被安排“下一次自动排版前强制重解析”时才执行重载
        should_reparse = bool(self._force_reparse_on_next_auto_layout)
        if not should_reparse:
            return
        
        # 保存当前视图的缩放与中心（场景坐标系下的中心点）
        prev_center_scene = None
        prev_scale = 1.0
        if self.view is not None:
            viewport_center = self.view.viewport().rect().center()
            prev_center_scene = self.view.mapToScene(viewport_center)
            prev_scale = self.view.transform().m11()
        
        # 清除该图的内存与持久化缓存，使后续加载直接解析 .py
        reparse_result = self._auto_layout_prepare_service.reparse_graph_from_py(
            resource_manager=self.resource_manager,
            graph_id=graph_id,
        )
        # 通知主窗口统一失效 GraphDataService / 图属性面板等上层缓存，避免仍拿到旧数据。
        self.graph_runtime_cache_updated.emit(graph_id)
        
        # 重新加载并替换到场景（使用解析结果中的 data 字段）
        if reparse_result.graph_data:
            self.load_graph(graph_id, reparse_result.graph_data, container=self.current_graph_container)
        
        # 恢复视图缩放与中心，避免用户视角跳变
        if self.view is not None and prev_center_scene is not None:
            self.view.resetTransform()
            self.view.scale(float(prev_scale), float(prev_scale))
            self.view.centerOn(prev_center_scene)
        
        # 清除一次性标记
        self._force_reparse_on_next_auto_layout = False

    def load_graph_for_composite(
        self,
        composite_id: str,
        graph_data: dict,
        *,
        composite_edit_context: dict,
    ) -> None:
        """加载复合节点子图到编辑器（含预排版与复合上下文注入）。

        设计目标：
        - 由控制器统一负责对子图做一次预排版（LayoutService.compute_layout）；
        - 将复合节点专用的 composite_edit_context 通过 scene_extra_options 注入 GraphScene；
        - UI 层仅关心“当前选中的复合节点 ID 与其子图数据”，不再手动构造场景与批量 add_node/add_edge。
        """
        if not graph_data or not isinstance(graph_data, dict):
            raise ValueError("复合节点子图数据为空或类型错误")

        # 1) 在当前进程内对复合节点子图做一次事件区域预排版（不落盘，仅调整位置语义）。
        pre_layout_model = GraphModel.deserialize(graph_data)
        LayoutService.compute_layout(pre_layout_model, clone_model=False)
        layouted_graph_data = pre_layout_model.serialize()

        # 2) 注入复合节点编辑上下文（仅对本次加载生效）：由 GraphScene 消费，用于端口同步与虚拟引脚回调。
        # 注意：不写入控制器全局 `_scene_extra_options`，避免污染后续普通图加载。
        scene_extra_options_override = {
            "composite_edit_context": dict(composite_edit_context or {}),
        }

        # 3) 复用通用加载管线，确保布局/场景装配/小地图等行为与普通图一致。
        effective_graph_id = composite_id or "composite_graph"
        self._load_graph_pipeline(
            GraphEditorLoadRequest(
                graph_id=effective_graph_id,
                graph_data=layouted_graph_data,
                container=None,
                scene_extra_options_override=scene_extra_options_override,
            ),
        )

    def load_graph(self, graph_id: str, graph_data: dict, container=None) -> None:
        """加载节点图
        
        Args:
            graph_id: 节点图ID
            graph_data: 节点图数据
            container: 容器对象（模板或实例）
        """
        self._load_graph_pipeline(GraphEditorLoadRequest(graph_id=graph_id, graph_data=graph_data, container=container))

    def _load_graph_pipeline(self, load_request: GraphEditorLoadRequest) -> None:
        """统一的节点图加载管线。

        说明：
        - 公共入口 `load_graph` 与复合入口 `load_graph_for_composite` 统一走此处，减少“改一点牵一片”。
        - `scene_extra_options_override` 为“单次加载 override”，不写入控制器全局 `_scene_extra_options`。
        """
        graph_id = load_request.graph_id
        container = load_request.container

        print(f"[加载] 开始加载节点图: {graph_id}")

        load_result = self._load_service.load(
            request=load_request,
            current_scene=self.scene,
            view=self.view,
            node_library=self.node_library,
            edit_session_capabilities=self._session_state_machine.capabilities,
            base_scene_extra_options=self._scene_extra_options,
            get_current_package=self.get_current_package,
            main_window=self.parent(),
            on_graph_modified=self._on_graph_modified,
        )

        # 更新引用：后续行为必须基于新的 model/scene
        self.model = load_result.model
        self.scene = load_result.scene

        # 会话能力同步到 view/scene（含 read_only 与“添加节点”入口）
        self._apply_edit_session_capabilities_to_view_and_scene()

        # 收尾：状态、验证与通知信号
        self._finalize_after_graph_loaded(graph_id=load_result.graph_id, container=container, baseline_hash=load_result.baseline_content_hash)

    def _finalize_after_graph_loaded(self, *, graph_id: str, container: object | None, baseline_hash: str) -> None:
        # 更新当前图状态
        new_status = self._session_state_machine.on_graph_loaded(graph_id=str(graph_id), baseline_content_hash=str(baseline_hash))
        self.current_graph_container = container

        self.save_status_changed.emit(new_status)

        from engine.configs.settings import settings as _settings_ui
        if getattr(_settings_ui, "GRAPH_UI_VERBOSE", False):
            print(f"[加载] 完成，加载了 {len(self.scene.node_items)} 个节点")

        # 加载完成后清除错误状态（如果有的话）
        self.error_tracker.clear_error(graph_id)

        # 加载完成后触发验证（需显式允许 can_validate）
        if self._session_state_machine.capabilities.can_validate and self._session_state_machine.capabilities.can_persist:
            self.validate_current_graph()

        # 发送加载完成信号
        self.graph_loaded.emit(graph_id)
    
    def save_current_graph(self) -> None:
        """保存当前节点图（仅当内容变化时）
        
        统一保存入口：所有节点图保存必须通过此方法
        - 保存前：验证数据完整性
        - 保存中：序列化并生成代码
        - 保存后：验证结果并更新UI
        """
        if not self.current_graph_id:
            return
        
        # 计算当前内容哈希（不含位置信息）
        current_hash = self.model.get_content_hash()
        if not self._session_state_machine.has_unsaved_changes(current_content_hash=current_hash):
            return
        
        # 不可保存会话：不写入资源（避免“看起来能保存”），仅维持基线与只读提示。
        if not self._session_state_machine.capabilities.can_persist:
            print(f"[保存] 当前会话不可保存（不落盘），跳过写入: {self.current_graph_id}")
            new_status = self._session_state_machine.on_modified(current_content_hash=current_hash)
            self.save_status_changed.emit(new_status)
            return
        
        # 非只读：正常保存
        print(f"[保存] 检测到内容变化，开始保存: {self.current_graph_id}")
        self.save_status_changed.emit(self._session_state_machine.on_save_started())

        save_result = self._save_service.save_graph(
            resource_manager=self.resource_manager,
            graph_id=str(self.current_graph_id),
            model=self.model,
        )
        if not save_result.success:
            error_message = save_result.error_message or "节点图保存失败"
            print(f"❌ [保存] 保存被阻止: {self.current_graph_id}")
            print(f"   原因: {save_result.error_code or 'unknown_error'}")
            self.save_status_changed.emit(self._session_state_machine.on_save_failed())
            self.error_tracker.mark_error(
                self.current_graph_id,
                error_message,
                str(save_result.error_code or "save_failed"),
            )
            return

        self.save_status_changed.emit(self._session_state_machine.on_save_succeeded(new_baseline_content_hash=current_hash))
        print(f"✅ [保存] 完成: {self.current_graph_id}")
        self.error_tracker.clear_error(self.current_graph_id)
        if self._session_state_machine.capabilities.can_validate:
            self.validate_current_graph()
        self.graph_saved.emit(self.current_graph_id)
    
    def validate_current_graph(self) -> None:
        """验证当前编辑的节点图并更新UI显示"""
        if not self._session_state_machine.capabilities.can_validate:
            return
        if not self.get_current_package or not self.get_property_panel_object_type:
            return
        
        current_package = self.get_current_package()
        if not current_package or not self.current_graph_container:
            return

        # 确定实体类型（由验证服务推导）
        object_type = self.get_property_panel_object_type()

        issues = self._validate_service.validate_for_ui(
            model=self.model,
            resource_manager=self.resource_manager,
            current_package=current_package,
            current_container=self.current_graph_container,
            object_type=str(object_type or ""),
            graph_id=str(self.current_graph_id or ""),
        )

        self.scene.update_validation(issues)
        self.graph_validated.emit(issues)
    
    def add_node_at_position(self, node_def: NodeDef, scene_pos: QtCore.QPointF) -> None:
        """添加节点"""
        print(f"[添加节点] 准备添加节点: {node_def.name}")
        print(f"[添加节点] 添加前Model中有 {len(self.model.nodes)} 个节点")
        
        node_id = self.model.gen_id("node")

        # 新建节点的“初始端口策略”统一收敛到 flow service，避免控制器硬编码业务分支。
        input_names = derive_initial_input_names_for_new_node(node_def)

        cmd = AddNodeCommand(
            self.model,
            self.scene,
            node_id,
            node_def.name,
            node_def.category,
            input_names,
            node_def.outputs,
            pos=(scene_pos.x(), scene_pos.y())
        )
        self.scene.undo_manager.execute_command(cmd)
        
        print(f"[添加节点] 添加后Model中有 {len(self.model.nodes)} 个节点")
        print(f"[添加节点] Scene.model中有 {len(self.scene.model.nodes)} 个节点")

    def _on_graph_modified(self) -> None:
        """节点图被修改时的回调 - 触发自动保存"""
        current_hash = self.model.get_content_hash()
        if not self._session_state_machine.capabilities.can_persist:
            # 不落盘会话：保持“只读/不落盘”提示，并将当前快照视为基线，避免把包标记为脏。
            self.save_status_changed.emit(self._session_state_machine.on_modified(current_content_hash=current_hash))
            return

        # 可保存会话：标记为脏状态并按全局设置触发自动保存
        self.save_status_changed.emit(self._session_state_machine.on_modified(current_content_hash=current_hash))

        # 基于全局设置的自动保存防抖（单位：秒；0 表示立即保存）
        from engine.configs.settings import settings as _settings
        interval_seconds = float(getattr(_settings, "AUTO_SAVE_INTERVAL", 0.0) or 0.0)
        if interval_seconds <= 0.0:
            self.save_current_graph()
            return
        # 延迟保存：合并短时间内的频繁修改
        if self._save_debounce_timer is None:
            self._save_debounce_timer = QtCore.QTimer(self)
            self._save_debounce_timer.setSingleShot(True)
            self._save_debounce_timer.timeout.connect(self.save_current_graph)
        # 重启计时器
        self._save_debounce_timer.start(int(interval_seconds * 1000))
    
    def mark_as_dirty(self) -> None:
        """标记节点图为未保存状态"""
        if not self._session_state_machine.capabilities.can_persist:
            return
        current_hash = self.model.get_content_hash()
        self.save_status_changed.emit(self._session_state_machine.on_modified(current_content_hash=current_hash))
    
    def mark_as_saved(self) -> None:
        """标记节点图为已保存状态"""
        current_hash = self.model.get_content_hash()
        self.save_status_changed.emit(self._session_state_machine.on_save_succeeded(new_baseline_content_hash=current_hash))
    
    @property
    def is_dirty(self) -> bool:
        """判断是否有未保存的修改"""
        current_hash = self.model.get_content_hash() if self.model is not None else None
        return self._session_state_machine.has_unsaved_changes(current_content_hash=current_hash)
    
    def open_graph_for_editing(self, graph_id: str, graph_data: dict, container=None) -> None:
        """打开节点图进行编辑（从属性面板触发）"""
        print(f"[EDITOR] open_graph_for_editing: graph_id={graph_id}, container={'Y' if container else 'N'}")
        # 保存当前节点图
        if self.current_graph_id and self.current_graph_container:
            self.save_current_graph()
        
        # 切换到节点图编辑页面
        self.switch_to_editor_requested.emit()
        print("[EDITOR] 已发出 switch_to_editor_requested 信号")
        
        # 加载节点图
        self.load_graph(graph_id, graph_data, container)
        print("[EDITOR] 已加载图数据到编辑视图")

        # 首次进入编辑视图后，自动适配全图到可视区域（延迟到下一帧，确保视口尺寸有效）
        QtCore.QTimer.singleShot(100, lambda: self.view and self.view.fit_all(use_animation=False))
    
    def open_independent_graph(self, graph_id: str, graph_data: dict, graph_name: str) -> None:
        """打开独立节点图（从节点图库触发）"""
        # 如目标与当前相同：直接切换到编辑器，避免重复装载
        if self.current_graph_id == graph_id:
            self.switch_to_editor_requested.emit()
            self.title_update_requested.emit(f"节点图: {graph_name}")
            QtCore.QTimer.singleShot(100, lambda: self.view and self.view.fit_all(use_animation=False))
            return
        
        # 保存当前节点图
        if self.current_graph_id and self.current_graph_container:
            self.save_current_graph()
        
        # 加载节点图配置
        graph_config = GraphConfig.deserialize(graph_data)
        
        # 切换到节点图编辑页面
        self.switch_to_editor_requested.emit()
        
        # 加载节点图数据（独立节点图没有容器）
        self.load_graph(graph_id, graph_config.data, container=None)
        
        # 切换进入编辑视图后，自动适配全图
        QtCore.QTimer.singleShot(100, lambda: self.view and self.view.fit_all(use_animation=False))
        
        # 更新窗口标题
        self.title_update_requested.emit(f"节点图: {graph_name}")
    
    def close_editor_session(self) -> None:
        """关闭当前节点图编辑会话并恢复空场景，用于清理缓存或强制返回列表。"""
        had_graph = bool(self.current_graph_id)
        if had_graph:
            self.save_current_graph()
        if self._save_debounce_timer and self._save_debounce_timer.isActive():
            self._save_debounce_timer.stop()
        if self.scene:
            self.scene.clear()
            if hasattr(self.scene, "node_items"):
                self.scene.node_items.clear()
            if hasattr(self.scene, "edge_items"):
                self.scene.edge_items.clear()
            if hasattr(self.scene, "undo_manager") and self.scene.undo_manager:
                self.scene.undo_manager.clear()
        self.model = GraphModel()
        self.scene = GraphScene(
            self.model,
            read_only=True,
            node_library=self.node_library,
            edit_session_capabilities=EditSessionCapabilities.read_only_preview(),
        )
        self.scene.undo_manager.on_change_callback = None
        self.scene.on_data_changed = None
        if self.view is not None:
            self.view.setScene(self.scene)
            self.view.resetTransform()
            self.view.viewport().update()
        self._session_state_machine.on_graph_closed()
        self.current_graph_container = None
        self._force_reparse_on_next_auto_layout = False
        self.set_edit_session_capabilities(EditSessionCapabilities.read_only_preview())
        self.title_update_requested.emit("节点图: 未打开")
    
    def refresh_persistent_cache_after_layout(self) -> None:
        """将当前模型写入持久化缓存（用于自动排版后覆盖缓存）。
        
        位置变化不落盘，但希望下次打开时直接使用最新位置，
        因此在自动排版完成后，将当前 GraphModel 序列化并写入 app/runtime/cache/graph_cache。
        """
        if not self.current_graph_id or not self.model:
            return
        graph_id = str(self.current_graph_id)
        result_data = self._auto_layout_prepare_service.build_persistent_cache_payload(graph_id=graph_id, model=self.model)
        self.resource_manager.update_persistent_graph_cache(graph_id, result_data)
        print(f"[缓存] 已刷新持久化缓存（自动排版后）: {graph_id}")

        # 通知主窗口统一失效 GraphDataService / 图属性面板等上层缓存，避免“显示不一致/回退”。
        self.graph_runtime_cache_updated.emit(graph_id)
        # 自动排版完成后：在编辑视图中自动适配全图并居中显示
        if self.view is not None:
            QtCore.QTimer.singleShot(100, lambda: self.view and self.view.fit_all(use_animation=False))

    def get_current_model(self) -> GraphModel:
        """获取当前模型"""
        return self.model
    
    def get_current_scene(self) -> GraphScene:
        """获取当前场景"""
        return self.scene

    def set_scene_extra_options(self, options: dict) -> None:
        """设置场景额外参数（例如复合节点编辑上下文）
        
        Args:
            options: 传入 GraphScene 的关键字参数字典
        """
        self._scene_extra_options = options or {}

