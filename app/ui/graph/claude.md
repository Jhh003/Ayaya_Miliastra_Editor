# 节点图编辑子包（ui/graph/）

## 目录用途
`ui/graph/` 集中承载“节点图编辑器”及其周边库页面相关的 PyQt6 UI 组件与辅助模块，包括：
- 图场景、视图与撤销栈
- 节点/连线/端口等图形项（QGraphicsItem）
- 节点图库页面与通用库页面 Mixin
- 元件库与实体摆放等“资源库视图”，通过统一的左右分栏脚手架与分类树 Mixin 构建

本子包只负责 UI 与交互层，不直接负责资源持久化；节点图和模板/实例/关卡实体等资源的解析与保存统一委托给 `engine/resources` 与上层控制器。

## 当前状态
- 提供图场景、图视图与相关交互组件，用于节点图的编辑与只读预览；`GraphView` 统一暴露滚轮缩放、平移、自动排版、小地图与“跳转到图元素”等信号能力（推荐从 `app.ui.graph.graph_view` 导入，该模块作为导入门面稳定指向 `graph_view_impl.py`，避免动态加载导致重复类对象）。
- 图形项、视图、图库页面等已按职责拆分到子目录，便于在不影响整体结构的前提下演进单个模块；图视图层支持通过 `graph_element_clicked` 信号向上层报告节点/连线/空白区域的单击事件，供任务清单等页面在只读预览模式下做联动高亮，并在重绘阶段统一同步小地图和右上角浮动控件的位置与层级，确保这些辅助控件在窗口与布局变化后依旧贴合视图边缘显示。
- 画布复用：`graph_canvas_host.py` 提供 `GraphCanvasHost`，用于承载并在不同页面之间移动同一个 `GraphView`（典型场景：任务清单预览与图编辑器共享 `app_state.graph_view`），避免 “QStackedWidget 页直接持有 GraphView” 导致的 parent 限制。
- 只读语义收敛：`GraphView.set_edit_session_capabilities()` 会根据 `EditSessionCapabilities` 控制自动排版按钮显隐（仅在允许交互+允许校验时显示）；`GraphScene.set_edit_session_capabilities()` 除了同步节点可拖拽外，也会同步禁用/恢复行内常量编辑控件（文本/下拉/向量等），确保只读预览不会出现“仍可改常量”的旁路编辑。
- 各类图库/资源库页面复用统一的搜索与过滤 Mixin，以及集中封装的“列表刷新 + 选中策略”助手函数，用于在刷新列表时恢复选中/在列表为空时收起右侧面板，并通过标准化的确认/提示对话框保持交互风格一致。
- `library_mixins.SearchFilterMixin` 提供 `ensure_current_item_visible_or_select_first(...)`，用于在搜索过滤后当“当前选中项被隐藏”时自动选中第一条可见记录，避免右侧详情仍停留在已被过滤的上下文。
- 元件库与实体摆放页共用实体分类树构建逻辑：实体摆放页的“📁 全部实体”分类会聚合当前视图下所有实体实例，并在存在关卡实体时追加一行“关卡实体”记录，关卡实体也可以通过专门的“📍 关卡实体”分类单独查看；分类树与列表项的实体类型图标统一通过 `engine.graph.models.entity_templates.get_entity_type_info` 获取。
- 图场景在端口类型、布局前处理与自动连线等方面遵循引擎层规则，不在 UI 层复制业务逻辑。
- GraphScene 初始化时会从 settings 的 workspace 单一真源构建 `layout_registry_context`（LayoutRegistryContext），供节点图形项与自动排版流程显式注入端口规划/高度估算所需的注册表派生信息，避免 UI 与布局层出现“按文件位置猜 workspace_root”的隐式回退差异。
- `GraphScene.add_node_item()` 负责在 `addItem()` 之后触发 `NodeGraphicsItem` 的端口布局，确保图形项在布局阶段可通过 `self.scene()` 获取场景上下文（含 `layout_registry_context`）。
- 批量装配大图（`scene_builder.populate_scene_from_model(enable_batch_mode=True)`）时，连线创建会延迟触发目标节点端口重排，并在装配结束后通过 `GraphScene.flush_deferred_port_layouts()` 统一刷新，避免逐边重排导致的卡顿。
- `scene_builder.populate_scene_from_model(...)` 的批量装配模式使用“必恢复”语义：即使装配过程中抛错，也会在 finally 中恢复 `GraphScene.is_bulk_adding_items`，避免后续交互误判仍处于批量模式。
- `logic/` 子目录集中放置信号/结构体节点的纯逻辑层（绑定解析、端口规划、NodeDef 代理），无 PyQt 依赖，供 UI 服务与单元测试复用。
 - 信号节点相关服务（如 `signal_node_service.py`）会在 UI 层基于当前包的信号配置为“发送信号/监听信号”节点补全端口与类型，并约定节点上【信号名】端口仅使用信号的显示名称进行匹配与展示；稳定绑定通过节点隐藏常量 `node.input_constants["__signal_id"]` 承载，并在变更后触发 `engine.graph.semantic.GraphSemanticPass` 覆盖式生成 `metadata["signal_bindings"]`，避免 UI/解析/IR 多源写入互相覆盖。
 - 结构体节点相关服务（如 `struct_node_service.py`）会基于结构体定义为“拆分结构体/拼装结构体/修改结构体”节点补全字段端口与类型：结构体选择结果写入节点隐藏常量 `node.input_constants["__struct_id"]` 与展示用的【结构体名】常量，并在端口同步后触发 `engine.graph.semantic.GraphSemanticPass` 覆盖式生成 `metadata["struct_bindings"]`；构建图形项前若模型已包含 struct_bindings，场景会基于绑定信息补全字段端口。
 - `GraphScene` 的“右键菜单桥接”已从主文件剥离到 `app.ui.scene.view_context_menu_mixin.SceneViewContextMenuMixin`；
   信号/结构体节点的菜单项与节点创建前的模型预处理统一由 `signal_node_service.py` / `struct_node_service.py` 提供（`contribute_context_menu_for_node` / `prepare_node_model_for_scene`），避免 `GraphScene` 直接硬编码业务分支。
- `GraphView` 与场景/交互的协作接口显式化：视图右键菜单仅委托 `SceneViewContextMenuMixin.handle_view_context_menu(...)`；场景侧弹出“添加节点”菜单统一调用 `GraphView.show_add_node_menu(...)`（公开方法），不依赖私有钩子探测。
- 复合节点编辑器上下文（`GraphScene.composite_edit_context`）中的“是否允许落盘写回”使用 `can_persist: bool` 作为唯一语义字段；撤销栈与虚拟引脚清理逻辑会以该字段决定是否调用 `CompositeNodeManager.update_composite_node` 写回文件。

## 注意事项
- 新增或扩展“图编辑”相关模块（场景/视图/图形项/图库页面等）时，应优先放入本目录，而非 `ui/` 根目录。
- 需要被管理面板或其他业务页面复用的能力，优先通过控制器或服务类暴露入口，避免在纯 UI 组件中掺入业务规则。
- 遵循项目约定：UI 层不使用 `try/except` 兜底，异常直接抛出，由上层入口统一处理。

