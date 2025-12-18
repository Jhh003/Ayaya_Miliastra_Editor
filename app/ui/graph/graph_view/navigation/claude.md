## 目录用途
封装 `GraphView` 视口导航逻辑，提供居中、适配、聚焦矩形与动画过渡等操作，避免在视图或控制器中重复实现几何计算。

## 当前状态
- `viewport_navigator.py` 暴露 `center_on_node/fit_all/focus_on_node/focus_on_nodes_and_edge/execute_focus_on_rect` 等静态方法，其中 `fit_all` 支持通过 `use_animation` 显式控制是否使用平滑过渡。
- 聚焦算法统一使用 `QtCore.QRectF` 进行扩展与 padding，并根据 `GraphView.enable_smooth_transition` 选择是否使用 `ViewTransformAnimation`。

## 注意事项
- 所有方法需要 `GraphView.scene()` 返回有效场景，在场景未就绪时务必跳过调用。
- `execute_focus_on_rect` 会暂时修改视图的 `transformationAnchor` 与 `resizeAnchor`，完成后会恢复；不可在调用期间再次嵌套外部 `fitInView`。
- 当图形项缺失或 ID 不存在时直接返回，保持“无副作用”原则，避免在调用方还原额外状态。
- `focus_on_node` / `focus_on_nodes_and_edge` 支持 `use_animation` 关键字参数，可按调用场景覆盖视图默认的平滑设置。

