# wiring/ 目录

## 目录用途
存放主窗口的“装配/连线（wiring）”代码：把各页面/面板对外发出的信号统一绑定到主窗口回调或 `NavigationCoordinator.handle_request(UiNavigationRequest)`。

## 当前状态
- 页面与面板的实例化仍由 `ui_setup_mixin.py` 负责（创建 Widget、注入依赖）。
- 具体的信号连接、导航请求构造与转发集中在本目录的 binder 函数中：
  - 页面级 binder：Todo/验证/图库/存档库/管理页的信号绑定与跳转请求转发；
  - 右侧面板 binder：属性面板/战斗详情/管理编辑页/验证详情等右侧面板的信号连接集中管理。
  以避免在 `ui_setup_mixin.py` 中堆积大量 `.connect(...)` 与闭包逻辑。
- 右侧标签注册表的“tab_id/标题/模式约束”矩阵配置已迁移到 `ui/main_window/features/RightPanelAssemblyFeature`，以减少新增右侧面板时的多点修改。
- `right_panel_registry_config.py` 已移除：避免出现“双真源”与隐式回退路径。
- 部分“新增功能高频扩展点”（例如右侧动态面板）允许迁移到 `ui/main_window/features/`：Feature 可以在 registry 初始化后自行创建控件并注册 tab，避免为新增面板同时改 `ui_setup_mixin.py + right_panel_registry_config.py + 若干 mixin`。

## 注意事项
- 本目录只做“连线”，不承载业务编排；复杂流程应下沉到 `app/models`（纯逻辑）或 UI 侧的专用 controller/service 模块。
- 导航请求必须通过 `app.models.UiNavigationRequest` 的工厂方法构造，避免在各处手写 `resource_kind/desired_focus` 字符串组合导致语义漂移。
- Todo 页面对外只暴露稳定信号（如 `todo_checked/jump_to_task`）；Todo 预览的“跳转到图元素”信号来自全局唯一的 `app_state.graph_view.jump_to_graph_element`，binder 侧需按当前 `ViewMode.TODO` 做门禁，避免编辑器中的双击事件被 Todo 跳转逻辑误处理。


