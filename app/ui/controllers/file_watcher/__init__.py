"""file_watcher 子模块：拆分 FileWatcherManager 的实现细节。

对外稳定入口仍然是 `app.ui.controllers.file_watcher_manager.FileWatcherManager`。
本目录仅提供其内部协作组件，避免主窗口层的 watcher 逻辑继续膨胀。
"""


