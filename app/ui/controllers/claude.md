# Controllers 模块

## 目录用途
控制器层，负责分离主窗口的业务逻辑，通过信号槽实现松耦合通信。每个控制器负责一个独立的功能域。

## 关键文件
- `package_controller.py`：功能包生命周期管理（创建、加载、保存、导入、导出）。保存链条采用“脏块 + service 编排”：`PackageDirtyState` 记录图/模板/实例/战斗/管理/索引等脏块，提供 `save_dirty_blocks()` 按脏块增量落盘；保存前通过主窗口注入的回调 `flush_current_resource_panel` 刷新右侧属性面板中使用去抖写回的基础信息编辑内容（名称/描述/GUID 等），避免字段停留在 UI 缓冲区；保存事务编排与写盘细节已下沉到 `ui/controllers/package_save/`，控制器仅委托 `PackageSaveOrchestrator` 执行“指纹基线同步 → 可选 flush → special_view / package_view 分支 → 索引写盘/指纹刷新”的顺序化流程；窗口关闭阶段遵循“flush → 按脏块保存”的策略，避免外部资源刷新后被无意义覆盖。
- `package_dirty_state.py`：存档脏块模型（保存链条的 UI 侧增量落盘入口使用）。
- `package_save/`：存档保存链条 service（见该目录 `claude.md`）。
- `graph_editor_controller.py`：节点图编辑核心逻辑（加载、保存、验证、节点添加）
  - 控制器仅负责信号转发与依赖注入：load/save/validate/auto_layout_prepare 等跨域链路已下沉到 `ui/controllers/graph_editor_flow/` 的纯流程 service，避免 God Object 继续膨胀。
  - 节点创建的业务特例（例如“拼装字典”默认键值对端口）集中维护在 `ui/controllers/graph_editor_flow/new_node_ports_policy.py`，控制器不再按节点名硬编码分支。
  - 会话能力/只读语义/保存状态由 `GraphEditorSessionStateMachine` 统一派生（单一真源），禁止 controller/view/scene 分别维护 read_only/dirty/saving 等状态导致分叉。
  - 为复合节点页面提供专用入口 `load_graph_for_composite(composite_id, graph_data, composite_edit_context=...)`：在控制器内部完成一次 `LayoutService.compute_layout(..., clone_model=False)` 的预排版；复合节点专用的 `composite_edit_context` 通过“单次加载 options override”注入 `GraphScene`（不写入全局 `_scene_extra_options`，避免污染后续普通图加载）。
  - 支持从节点图库双击打开**独立节点图**：通过 `open_independent_graph(graph_id, graph_data, graph_name)` 配合 `engine.graph.models.GraphConfig` 反序列化图配置，再调用统一的 `load_graph` 路径加载 `GraphModel`，保证独立节点图在编辑器中的数据结构与引擎侧配置模型保持一致
  - 加载路径在反序列化与复合端口同步之后，直接使用资源层 `ResourceManager.load_resource(ResourceType.GRAPH, ...)`/`GraphResourceService.load_graph` 产出的已布局数据（含跨块复制、副本去重与基本块信息），不在 UI 层重复调用 `engine.layout.LayoutService.compute_layout`，确保编辑器视图与 `app/runtime/cache/graph_cache` 中的布局保持一致，避免“第二次布局”产生多余副本或视图与缓存不一致。
  - 默认运行于**逻辑只读模式**：屏蔽添加/删除/连线等会改变节点图结构的命令，自动保存不响应场景逻辑变更；显式保存时会从磁盘重新加载已有 `GraphConfig`，仅在允许的字段发生变化时合并并写回，不改动节点/连线/常量等逻辑：
  - 合并节点图变量 `graph_variables`（在当前 UI 策略下，变量编辑控件默认处于禁用或只读状态，避免从界面触发落盘写入）
  - 合并允许的元信息：`graph_name`、`metadata`（例如统计时间等），用于与属性面板的元信息编辑保持一致
  - 若检测到仅逻辑结构（节点/连线/常量）发生变更而变量与元信息未变，则在只读模式下拒绝保存并将状态标记为“未保存”，同时通过信号提示 UI，这类逻辑修改需要在非只读上下文中由外部工具处理。
  - 只读模式下：不在加载/保存后触发 UI 层的 `validate_current_graph()`，以避免不必要的校验提示；仍保留保存时的往返验证，用于保障外部文件变更的正确性。
  - 切换到编辑页面后：自动适配视图到全图（调用 `fit_all(use_animation=False)`），确保首次进入能看到所有节点且镜头瞬间定位（延迟一帧执行以保证视口尺寸有效）
  - 提供 `refresh_persistent_cache_after_layout()`：在自动排版完成后由视图层回调触发，先将当前 `GraphModel` 序列化并写入持久化缓存（覆盖旧缓存），随后通过 `graph_runtime_cache_updated(graph_id)` 信号通知主窗口统一失效上层缓存（GraphDataService 的 GraphModel/payload 缓存、图属性面板数据提供器等），避免 UI 中分散维护“需要清一串缓存”的链条；最后通过 `GraphView.fit_all(use_animation=False)` 自动适配全图并瞬间居中显示，下一次加载直接使用最新位置（不修改源 .py）。
  - 提供一次性排版前准备：`schedule_reparse_on_next_auto_layout()` + `prepare_for_auto_layout()`，用于在“数据节点跨块复制”从 True→False 后的首次自动排版前，清除当前图的缓存并从 `.py` 重新解析以清除历史副本
  - 通过 `app.ui.graph.scene_builder.populate_scene_from_model()` 批量装配场景，编辑器与只读预览共用同一装配逻辑，避免多处维护 `for node in model.nodes` 循环以及 `is_bulk_adding_items` 标记。
  - 提供 `close_editor_session()`：保存当前图后重置模型/场景/视图并清空 `current_graph_id`，用于设置页“清除缓存”等场景将用户送回节点图列表，确保内存与文件监控彻底脱钩。
  - 在场景批量装配完成后，会基于 `GraphModel.metadata["signal_bindings"]` 与当前包视图的 `signals` 字段，统一触发信号节点端口同步入口，为“发送信号/监听信号”节点追加缺失的参数端口并刷新端口类型，使节点图编辑器在重新打开已有图时也能立即反映最新的信号定义。
  - 对于早期写入的 `graph_cache`（仅记录 `signal_schema_hash` 但尚未补全参数端口），加载阶段会在哈希匹配但检测到发送/监听信号节点缺少定义中参数端口时强制重跑一次信号端口同步，从而修复节点图库/编辑器中动态参数端口缺失的问题，并为后续持久化缓存刷新提供已补全的模型结构。
- 当前图验证：通过 `engine.validate.ComprehensiveValidator` 执行，`GraphEditorController.validate_current_graph()` 使用 `ComprehensiveValidator.validate_graph_for_ui(...)` 将结构规则与挂载/作用域/结构告警/端口一致性统一成 UI 可用的问题列表（含节点级 detail 用于高亮）。
- `navigation_coordinator.py`：跳转协调（任务清单、验证面板、预览窗口、实体间跳转），以 `app.models.ui_navigation.UiNavigationRequest` 作为统一的“导航意图”数据模型，将来自任务清单 detail_info、验证问题 detail、图属性引用、图库/存档库点击以及管理面板等来源的原始上下文封装为 `UiNavigationRequest` 后，通过单一入口 `handle_request()` 解析出目标 `ViewMode`、需要选中的资源（模板/实例/关卡实体/管理 Section）以及是否需要打开节点图并定位到节点或连线；节点图数据解析与加载统一通过 `app.runtime.services.graph_data_service.GraphDataService`（内部桥接 `graph_data_key` 进程内缓存），避免在 UI 控件中持有整张图并减少“缓存分叉”。
- `validation_graph_code_service.py`：验证页面的“节点图源码校验”服务，统一收敛 `engine.validate.validate_files` + `collect_composite_structural_issues` 的调用与 EngineIssue→ValidationIssue 的 UI 适配（file/line_span/错误码与跳转 detail）。
- `file_watcher_manager.py`：文件系统监控与冲突解决的主窗口侧门面（facade），统一使用 `QFileSystemWatcher` 监听当前节点图 `.py` 文件与（启用自动刷新时）资源库目录树：整体链路坚持“目录事件→后台算指纹→对比基线→触发主窗口统一刷新入口”的单向确认，避免目录事件误触发刷新；**watcher 侧不提前推进指纹基线**，基线仅由主窗口 `refresh_resource_library()`→`ResourceRefreshService`→`ResourceManager.rebuild_index()` 在“失效 + 重建成功”后更新。具体实现按职责拆分到 `ui/controllers/file_watcher/`：`GraphFileWatchCoordinator` 负责图文件变更去抖、watcher 恢复、冲突检测与重载后视图状态恢复/撤销栈清理；`ResourceWatchRegistry` 负责资源库目录递归扫描（事件循环启动后后台扫描）与主线程分批 `addPath`，并在 `directoryChanged` 后增量补齐新目录 watcher；`ResourceAutoRefreshBridge` 负责将 `resource_library_auto_refresh_state_machine.py` 的纯逻辑动作桥接到 Qt 计时器/线程与主窗口刷新回调，并在 watcher 无法覆盖全部目录时启用“周期性指纹复核”兜底以降低漏刷新概率；当 `RESOURCE_LIBRARY_AUTO_REFRESH_ENABLED` 关闭时，仅保留当前图文件监控，资源库刷新依赖主窗口显式“更新”入口。
  - `resource_library_auto_refresh_state_machine.py`：资源库自动刷新纯逻辑状态机（事件→状态→动作），并将“刷新互斥 / 指纹复核 / 内部写盘抑制”做成可测试组件；内部写盘抑制支持“按目录粒度”缩小忽略范围（节点图保存仅抑制其所在目录，整包保存可沿用全局抑制），降低误吞其它目录外部新增资源事件的概率；对应最小回归在 `tests/ui/test_resource_library_auto_refresh_state_machine.py`。
  - 节点图文件变更处理采用可取消的单次计时器做去抖（合并 200ms 内的多次 fileChanged），避免重复触发重载；并在延迟回调中尝试恢复对图文件路径的 watcher，以兼容部分编辑器的“原子写入/重命名覆盖”保存方式导致的 watcher 丢失。
  - `cleanup()` 设计为幂等：支持被安全调用多次；信号断开使用“按槽函数精确 disconnect + 连接状态标记”，避免重复 disconnect 抛错；不再依赖 `__del__` 触发清理，资源释放统一由窗口关闭流程负责调用。
- `graph_error_tracker.py`：节点图错误状态跟踪（单例模式，记录保存失败的节点图）

## 注意事项补充
- 节点添加等图编辑命令统一通过 `app.ui.graph.graph_undo` 中的 UI 级命令类封装，并交由场景的 `UndoRedoManager` 管理，控制器层不直接依赖引擎内部的模型级命令实现。
- 用户提示与确认对话框统一走 UI 层封装：控制器自身不直接实例化 `QMessageBox`，而是通过 UI 控件的 `ConfirmDialogMixin` 或 `app.ui.foundation.dialog_utils` 暴露的函数触发弹窗，确保消息样式和行为与整体主题一致；涉及简单文本或类型选择时，同样应优先复用 `app.ui.foundation.input_dialogs` 提供的标准输入对话框，而不是直接使用 `QInputDialog`。

## 设计原则
- **单一职责**：每个控制器只负责一个功能域
- **信号通信**：控制器之间和控制器与UI之间通过PyQt6信号槽通信，避免直接依赖
- **依赖注入**：控制器通过构造函数接收必要的依赖（资源管理器、模型等）
- **回调函数**：对于需要访问主窗口状态的场景，使用lambda回调函数代替直接引用
- **异常处理约定**：不使用 `try/except` 掩盖错误；遇到错误直接抛出，由上层统一处理或中止流程，避免隐性回退或降级逻辑

## 信号设计规范

### PackageController 信号
- `package_loaded(str)` - 功能包加载完成，传递package_id
- `package_saved()` - 功能包保存完成
- `package_list_changed()` - 功能包列表发生变化
- `title_update_requested(str)` - 请求更新窗口标题
- `request_save_current_graph()` - 请求保存当前编辑的节点图

### GraphEditorController 信号
- `graph_loaded(str)` - 节点图加载完成，传递graph_id
- `graph_saved(str)` - 节点图保存完成，传递graph_id
- `graph_validated(list)` - 节点图验证完成，传递问题列表
- `validation_triggered()` - 触发验证
- `switch_to_editor_requested()` - 请求切换到编辑页面
- `title_update_requested(str)` - 请求更新窗口标题
- `save_status_changed(str)` - 保存状态变化（"saved" | "unsaved" | "saving" | "readonly"）

### GraphErrorTracker 信号
- `error_status_changed(str, bool)` - 错误状态变化（graph_id, has_error）

### NavigationCoordinator 信号
- `navigate_to_mode(str)` - 导航到指定模式
- `select_template(str)` - 选中模板
- `select_instance(str)` - 选中实例
- `select_level_entity()` - 选中关卡实体
- `open_graph(str, dict, object)` - 打开节点图
- `focus_node(str)` - 聚焦到节点
- `focus_edge(str, str, str)` - 聚焦到连线
- `load_package(str)` - 加载功能包
- `switch_to_editor()` - 切换到编辑器
- `open_player_editor()` - 打开玩家编辑器
 - `select_composite_name(str)` - 选择复合节点（按名称）
- `focus_management_section_and_item(str, str)` - 管理配置定位（section_key, item_id；item_id 允许为空表示仅切换 section）

### FileWatcherManager 信号
- `reload_graph_requested()` - 请求重新加载节点图
- `show_toast(str, str)` - 显示Toast通知（消息, 类型）
- `conflict_detected()` - 检测到冲突
- `graph_reloaded(str, dict)` - 节点图已重新加载（graph_id, graph_data）
- `force_save_requested()` - 强制保存本地版本

## 面向开发者的要点
- **避免循环信号**：确保信号连接不会造成循环触发，必要时使用`blockSignals()`
- **状态同步**：控制器间的状态通过信号同步，避免直接访问其他控制器的属性
- **空指针检查**：所有控制器方法都应检查必要的依赖是否已初始化
- **错误传播**：控制器内的错误通过信号传递给主窗口处理，或直接抛出
- **回调函数设置**：某些控制器需要访问主窗口状态，通过`get_xxx`回调函数实现（在主窗口的`_setup_controllers`中设置）

## 数据流示例

### 功能包加载流程
1. 用户在下拉框选择功能包 → `MainWindow._on_package_combo_changed`
2. → `PackageController.load_package(package_id)`
3. → `PackageController.package_loaded` 信号
4. → `MainWindow._on_package_loaded` 更新UI组件

### 节点图编辑流程
1. 用户在属性面板双击节点图 → `TemplateInstancePanel.graph_selected` 信号
2. → `MainWindow._on_graph_selected`
3. → `GraphEditorController.open_graph_for_editing`
4. → `GraphEditorController.switch_to_editor_requested` 信号
5. → `MainWindow` 切换到编辑页面
6. → `GraphEditorController.load_graph` 加载图数据

### 跳转流程（集中使用 UiNavigationRequest）
1. 用户在任务清单选中任务 → `TodoListWidget.jump_to_task` 信号（自动触发，携带 detail_info）
2. → `MainWindow.UISetupMixin._create_todo_page` 将 detail_info 包装为 `UiNavigationRequest(resource_kind="graph_task", origin="todo", payload=detail_info)` 并调用 `NavigationCoordinator.handle_request()`
3. → `NavigationCoordinator._handle_graph_request/_handle_graph_todo_detail`：根据 `detail_info.type` 与 `graph_id/template_id/instance_id` 决定切换到元件库/实体摆放/图编辑器/复合节点管理等模式，并通过 `open_graph` 与后续的 `_locate_graph_element` 在编辑器内完成节点/连线定位
4. → 验证面板、图属性面板、节点图库与存档库等其它导航源同样通过各自的 UISetupMixin 回调将业务上下文转成 `UiNavigationRequest`，统一交给 `NavigationCoordinator.handle_request()` 决定 `ViewMode` 切换与右侧属性/图属性面板的资源选中；`NavigationCoordinator` 不直接依赖任意具体 Widget 结构，只通过信号与主窗口及控制器协作完成跳转

## 注意事项与边界条件
- 控制器不直接操作UI组件，所有UI操作通过信号委托给主窗口。
- 控制器可以访问数据模型和资源管理器。
- 主窗口作为信号连接的中枢，在 `_connect_controller_signals` 中集中管理所有连接。
- 控制器之间的通信必须通过主窗口中转，不允许控制器直接引用其他控制器。
- `PackageController.save_package()` 保存存档时，需要确保任何仅存在于 `PackageView` 视图模型中的包级配置（例如信号配置、管理配置）都已序列化回写到对应的 `PackageIndex` 字段与管理配置资源文件，避免编辑器关闭后这些配置只停留在内存缓存中而未写入索引/资源库。
- **文件监控与场景刷新**：当复合节点库更新触发场景刷新时（`_refresh_current_graph_display()`），必须清除 undo_manager 历史，避免文件监控误判为有本地修改。
- **最近打开的选择**：支持记录并恢复 `<全部资源>`（`global_view`）模式，重启后会回到该模式。
- **加载性能建议**：加载大图时，先将 `GraphView.setUpdatesEnabled(False)`、`scene.undo_manager.on_change_callback=None`、`scene.on_data_changed=None`，并把 `QGraphicsScene.ItemIndexMethod` 设为 `NoIndex`；批量添加节点与连线完成后，由控制器统一调用场景的重建入口（重算场景矩形与小地图缓存），再恢复为 `BspTreeIndex`、恢复回调并启用视图更新，最后 `viewport().update()` 一次性刷新，避免在批量添加阶段对每个节点执行全图边界统计。
- **自动保存防抖**：非只读模式下，自动保存受到 `engine.configs.settings.Settings.AUTO_SAVE_INTERVAL` 控制（单位秒；0 表示每次修改立即保存），使用单次计时器合并短时间内的频繁修改。
- **小地图位置更新**：加载完成后使用 `ViewAssembly.update_mini_map_position(self.view)` 更新小地图位置。
- 资源访问：统一使用 `engine.resources.*`（`PackageView/GlobalResourceView/UnclassifiedResourceView`）。

## 当前状态
- 控制器层已稳定承担“主窗口业务逻辑分离”的角色，主窗口聚焦于视图装配与信号连接。
- 节点图加载、保存、验证、导航等关键交互均通过专门控制器协作完成，便于后续扩展与测试。

---
注意：本文件不记录任何修改历史。请始终保持对"目录用途、当前状态、注意事项"的实时描述。

