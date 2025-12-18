## 目录用途
封装 `GraphView` 右键菜单与上下文交互的桥接逻辑，当前主要包含“添加节点”弹窗的调度与自动连接流程。

## 当前状态
- `add_node_menu_bridge.py` 负责根据右键位置、端口过滤条件等信息构造 `AddNodePopup`，并在节点创建后触发自动连接。
- `__init__.py` 仅导出 `AddNodeMenuBridge`，确保 `app.ui.graph.graph_view.context` 提供稳定 API。

## 注意事项
- 需要 `GraphView` 已设置 `node_library` 与 `on_add_node_callback`；若任一缺失，桥接逻辑会直接返回，避免空引用。
- 组件仅负责 UI 层调度，实际节点创建/连线通过 GraphView 注入的回调完成，保持与控制器解耦。
- 关闭旧弹窗后再创建新弹窗，防止多个浮层同时存在导致的焦点错乱。

