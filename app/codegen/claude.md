## 目录用途
`app/codegen/` 存放**应用层/工具层**使用的代码生成器：把 `engine` 产出的中立产物（`GraphModel`/IR/节点库索引结果）序列化为可运行的 Python 源码（节点图 Graph Code、复合节点函数/类代码等）。

## 依赖边界
- 允许依赖：`engine/*`、`plugins/*`、`app/runtime/*`（以 `runtime.*` 顶层导入形式使用）
- 禁止依赖：`app/ui/*`（避免把 UI 逻辑引入生成器）、`core/*`

## 当前状态
- 节点图导出与复合节点导出的“可执行/可运行”代码生成器已迁入本目录；`engine` 不再包含运行时绑定的生成逻辑。
- 生成代码默认采用 `runtime.engine.graph_prelude_*`/资源库 `_prelude.py` 的导入策略：上层可通过参数选择导入模式、选择 server/client 预设以及是否启用 `@validate_node_graph`（校验入口默认指向 `engine.validate.node_graph_validator`）。
- 为避免 `ui.*` 与 `app.ui.*` 双导入，节点图/复合节点生成代码在 workspace_bootstrap 策略下只注入 `PROJECT_ROOT` 与 `ASSETS_ROOT` 到 `sys.path`，不注入 `<repo>/app`。
- 复合节点源码落盘统一生成**类格式（@composite_class）+ JSON payload**：文件内以 `COMPOSITE_PAYLOAD_JSON`（多行字符串）承载 `CompositeNodeConfig.serialize()`，避免触发复合节点校验规则中的“禁止 list/dict 字面量”，并确保 UI 可视化编辑后可闭环落盘与再次解析/校验。

## 注意事项
- 本目录只负责生成源码字符串，不负责写文件或管理资源索引；落盘与缓存由 `engine.resources`/上层 CLI 负责。
- 不在生成器里写判空/存在性分支来“兜底”，错误应直接抛出并由调用方暴露给用户。

---
注意：本文件不记录变更历史，仅描述目录用途、当前状态与注意事项。


