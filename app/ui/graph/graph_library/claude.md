## 目录用途
节点图库子模块，将 `ui/graph_library_widget.py` 中的领域逻辑抽取为职责明确的 mixin，使主组件专注于 UI 装配与状态管理：

- `folder_tree_mixin.py`：文件夹树展示与基础交互（右键菜单挂载、展开状态缓存、目标文件夹选择等）；在当前只读策略下，UI 层不再通过该 mixin 执行新增/重命名/删除文件夹或拖拽移动节点图等会导致持久化变更的操作，相关入口在逻辑层短路返回，仅保留浏览与定位能力。
- `graph_list_mixin.py`：节点图卡片列表（加载轻量元数据、排序/筛选、只读浏览与跳转、按 ID 选择与打开），内建 `_graph_metadata_cache` 与卡片快照，避免重复调用 `load_graph_metadata()` 并在内容未变更时跳过 UI 更新；根节点下的列表展示当前“类型”筛选下的所有节点图（不按 `folder_path` 额外过滤），点击左侧文件夹后列表范围收缩为该子树中的图；在节点图库的“仅所属存档可写”约束下，该 mixin 只负责根据筛选结果构建卡片并发出“选中/双击/跳转”信号，不再通过上下文菜单或按钮触发新建/重命名/删除/移动节点图及变量写回，所有持久化修改统一由右侧图属性面板的“所属存档”选择行写回包索引。
- 图卡片列表支持增量刷新：`GraphListMixin` 复用现有 `GraphCardWidget` 并记录排列顺序，仅在资源增删或卡片信息发生差异时创建/销毁/移动 QWidget，避免大规模的重建与布局抖动。

主组件 `GraphLibraryWidget` 只负责：UI 装配、样式应用、信号绑定与基础状态（`current_graph_type/current_folder/current_sort_by/current_package`），并确保整页遵守“除了设置所属存档之外不允许落盘修改节点图”的约束。

## 当前状态
- 图库页已切换为只读浏览模式：文件夹树与卡片列表仅承担筛选、定位与跳转，节点图的新增/重命名/删除及变量写回入口已关闭，归属写回统一由右侧图属性面板处理。
- `FolderTreeMixin` 维护 `(graph_type, folder_path)` 的展开快照按需重建树；`GraphListMixin` 依赖 `_graph_metadata_cache` 与卡片快照做增量刷新，避免大图量下的重建抖动。
- `GraphListMixin` 在刷新列表时会基于“资源库指纹 + 当前视图上下文 + 筛选条件”生成刷新签名；签名未变时跳过全量枚举与排序，复用现有卡片与选中状态，降低跨页面切换时的卡顿。
- 支持 server/client 类型切换与全局/未分类/按包过滤，筛选结果与 `PackageIndex` 的索引保持一致。

## 注意事项
- 事件过滤器：`FolderTreeMixin.eventFilter` 负责文件夹树拖拽，主组件需在 `_setup_ui` 中 `self.folder_tree.viewport().installEventFilter(self)`；若基类顺序因继承结构无法使 mixin 先于 `QWidget`，mix-in 内已回退调用 `QtWidgets.QWidget.eventFilter`，确保拖拽逻辑与默认处理兼容。
- Folder tree 会保存“已展开的 `(graph_type, folder_path)` 集合”并对比快照，仅当文件夹结构发生变化时才真正重建；普通刷新会尽量恢复原有展开状态，而在切换节点图类型（`force=True`）时会忽略旧展开快照并自动展开整棵树，确保从 server 切到 client 时也能直接看到各级子文件夹。
- 异常处理：遵循 UI 目录约定，不使用 try/except；异常直接抛出。确认/警告等需要用户决策的提示统一通过标准对话框或 `ConfirmDialogMixin` 处理，而文件夹删除成功等非关键状态反馈则使用 `ToastNotification.show_message()` 在窗口右上角短暂展示，不打断后续操作。
- 上下文菜单：统一使用 `app.ui.foundation.context_menu_builder.ContextMenuBuilder`，不要内联 QSS。
- 资源读写：仅通过 `ResourceManager` 读写图与文件夹信息；图列表加载使用 `load_graph_metadata()` 的轻量路径，避免执行节点图代码；对节点图包归属的修改统一委托右侧图属性面板中的 `PackageMembershipSelector` 和 `PackageIndexManager`，不在本子包中直接改写索引文件。
- 依赖：不引入主窗口或编辑器控制器引用；与外部交互统一通过 `GraphLibraryWidget` 的信号（`graph_selected/graph_double_clicked/jump_to_entity_requested`）。
- 资源访问：统一使用 `engine.resources.*`（`PackageView/GlobalResourceView/UnclassifiedResourceView/GraphReferenceTracker`）。
- UI 卡片：图卡片渲染统一来自 `app.ui.graph.library_pages.graph_card_widget.GraphCardWidget`，不要在 mixin 中定义平行实现；卡片上的“变量/编辑”等按钮在图库视图中为只读展示或禁用状态。
- 提示与确认：`GraphListMixin` 通过 `ConfirmDialogMixin` 的 `confirm/show_warning/show_error` 暴露统一入口，不再直接散落 `QMessageBox` 调用；`FolderTreeMixin` 中的“删除文件夹成功”等操作采用右上角的 Toast 通知替代阻塞信息框，保持删除流程轻量、可连续操作。


