## 目录用途
- 本目录承载“文件监控 / 资源库自动刷新”链路的**可复用组件**，用于将 `QFileSystemWatcher + 去抖 + 后台线程 + 指纹计算 + 刷新触发 + 冲突处理` 拆分为职责单一的模块。
- 目标是降低 `FileWatcherManager` 的复杂度：`FileWatcherManager` 仅作为主窗口侧门面（facade）与信号转发层，具体逻辑由本目录组件协作完成。

## 当前状态
- **图文件监控**：由 `graph_file_watch_coordinator.py` 负责处理 `fileChanged` 去抖、watcher 恢复、冲突检测、以及重载后视图状态恢复/撤销栈清理。
- **资源库 watcher 注册**：由 `resource_watch_registry.py` 负责后台扫描资源库目录树并在主线程分批 `addPath`，同时支持“新增目录增量补齐”以降低漏监听概率。
- **资源库自动刷新桥接**：由 `resource_auto_refresh_bridge.py` 将 `resource_library_auto_refresh_state_machine.py` 的纯逻辑动作（计时器/指纹计算/刷新请求）桥接到 Qt 计时器与后台线程；支持将“内部写盘抑制”按目录粒度记录，避免保存当前节点图时误吞其它目录的外部新增资源事件。

## 注意事项
- 本目录组件可以依赖 Qt（计时器、线程、信号），但**决策逻辑**应尽量保持在纯逻辑层（例如状态机）中，避免在 watcher 事件回调里堆叠策略判断。
- 不在本目录使用 `try/except` 吞异常；错误直接抛出，由上层统一中止或处理。


