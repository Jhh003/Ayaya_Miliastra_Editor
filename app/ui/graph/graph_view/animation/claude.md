## 目录用途
集中管理 `GraphView` 的变换动画，实现平滑缩放与平移过渡，供导航器与其他视图操作复用。

## 当前状态
- `view_transform_animation.py` 实现 `ViewTransformAnimation`，支持以帧动画方式插值缩放矩阵与视口中心，并在完成时恢复原始锚点。
- `__init__.py` 仅导出动画类，便于 `app.ui.graph.graph_view` 直接引用。

## 注意事项
- 动画运行依赖 `GraphView` 的 `transform_animation` 属性；在禁用平滑过渡时调用方应提前检查 `enable_smooth_transition`。
- 由于动画直接操作视图的 `QTransform`，并在过程中写入 `setTransformationAnchor`，务必避免并发启动多个动画实例。
- 动画类不负责任何业务逻辑，仅处理变换插值；完成后若需额外操作（如更新小地图），应在外部回调中触发。

