## 目录用途
管理 `GraphView` 右上角的浮动控件，包括自动排版按钮以及可注入的额外操作按钮（如预览页的“编辑”）。

## 当前状态
- `controls_manager.py` 提供 `ensure_auto_layout_button/update_position/set_extra_button/raise_all` 等静态方法，负责按钮创建、定位与层级维护。
- 按钮样式与交互在此集中定义，`GraphView` 仅在初始化和 resize 时调用接口，复用同一套体验。

## 注意事项
- 额外按钮必须以 `GraphView` 为父控件，避免层级错乱；管理器会自动调用 `raise_()` 保证置顶。
- 当视图尺寸发生变化或 `extra_top_right_button` 可见性改变时，请再次调用 `update_position`，否则按钮可能漂移。
- 按钮的点击逻辑应在外部连接（GraphView、控制器或面板），本目录不绑定业务行为，保持可复用性。
- 浮动按钮的配色（背景、文字、禁用态等）已改用 `ThemeManager.Colors` 主色与禁用色生成的 QSS，确保在浅色/深色主题下保持一致的对比度。

