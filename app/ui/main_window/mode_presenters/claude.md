## 目录用途
`ui/main_window/mode_presenters/` 提供“模式控制器/Presenter”体系：每个 `ViewMode` 对应一个 Presenter，专职承载“进入模式后的副作用”（刷新列表、懒加载页面、同步右侧上下文等）。

目标是让 `ModeSwitchMixin` 只保留公共切换流程（保存/切堆栈/收敛右侧/会话快照），并通过显式的 `MainWindowViewState` 作为单一真源减少隐式依赖与顺序依赖。

## 当前状态
- `coordinator.py`：`ModePresenterCoordinator`，负责按 `ViewMode` 分派到对应 presenter。
- `presenters.py`：各模式 presenter 的实现（TEMPLATE/PLACEMENT/COMBAT/MANAGEMENT/TODO/COMPOSITE/GRAPH_LIBRARY/VALIDATION/GRAPH_EDITOR/PACKAGES）。
  - 进入图库模式时统一调用库页协议 `reload()` 触发刷新与选中同步，不再依赖旧式 `refresh()` 入口。
  - 进入 `GRAPH_EDITOR` 时会将全局 `app_state.graph_view` 从其它 Host（例如 TODO 预览）归还到编辑器 Host，并恢复右上角浮动控件（“前往执行”按钮）与交互开关，避免跨模式复用画布导致的 UI 状态漂移。
  - 进入 `VALIDATION` 时优先触发“存档综合校验 + 节点图源码校验（当前存档范围）”，确保验证页面覆盖 UI 与 CLI 的核心规则集合，减少入口漂移。

## 注意事项
- Presenter 不直接读写磁盘，不吞异常；必要依赖缺失应直接抛出以暴露初始化顺序问题。
- Presenter 只做“进入模式副作用”，不要把模式切换的公共步骤（保存/右侧收敛/会话保存）搬进来。
- Presenter 只通过 `main_window.right_panel` 表达右侧标签的显隐意图；右侧“默认隐藏态”的统一收敛由 `ModeTransitionService` 调用 `right_panel.prepare_for_mode_enter(...)` 完成，避免在各 presenter 内重复写 hide 分支造成漂移。

---
注意：本文件不记录任何修改历史。请始终保持对"目录用途、当前状态、注意事项"的实时描述。


