## 目录用途
- 本目录承载 Todo 右侧详情面板的“结构化文档构建器”插件。
- 每个模块负责一组 `detail_type`（或前缀/谓词规则），并在导入时向 registry 注册 builder。

## 当前状态
- 详情文档的入口仍是 `app.ui.todo.todo_detail_renderer.TodoDetailBuilder.build_document()`，但其内部不再使用长链 if 分发，而是通过 `todo_detail_builder_registry` 查找已注册的 builder。
- 内置 builder 以“按领域拆分”的方式分布在本目录多个模块中（例如 root/category、template/instance、graph 相关等）。

## 注意事项
- 新增 detail_type 时：优先新增一个 builder 并在本目录注册；不要回到中心化 if-chain。
- Builder 代码应保持无 Qt 依赖，返回 `DetailDocument`；具体渲染由 `TodoDetailView` 完成。
- 不使用 try/except 吞异常；构建失败直接抛出，方便定位问题。


