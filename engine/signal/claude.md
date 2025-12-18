## 目录用途
- 集中承载信号系统的引擎层领域服务，包括“定义访问（DefinitionRepository）”“图模型绑定与使用统计（BindingService）”以及“代码生成适配（CodegenAdapter）”等纯逻辑组件。

## 当前状态
- `SignalDefinitionRepository` 基于 `engine.resources.definition_schema_view.DefinitionSchemaView` 聚合 `{signal_id: payload}` 只读视图，并提供按名称解析 ID 与“允许的参数名集合”等派生视图；仓库内部会对这些派生结果做二级缓存，并提供 `invalidate_cache()` / `invalidate_default_signal_repository_cache()` 作为显式失效入口，供资源库刷新与代码资源变更场景使用。
- `SignalBindingService` 负责围绕 `GraphModel.metadata["signal_bindings"]` 的读取与统计（图内概览、包级统计等）；写入由 `engine.graph.semantic.GraphSemanticPass` 作为单一写入阶段覆盖式生成，绑定“意图”通过节点隐藏常量 `__signal_id` 承载；`set_node_signal_id` 等直接写入接口视为废弃并禁止使用。
- `SignalCodegenAdapter` 为可执行代码生成器提供“信号节点 → emit_signal/register_event_handler”的统一适配层，屏蔽信号事件名与事件参数映射的细节，使代码生成逻辑无需直接操作 `signal_bindings` 或硬编码信号节点特例。
- `compute_signal_schema_hash` 基于当前包的 `{signal_id: SignalConfig}` 构造稳定的 schema 结构并计算 MD5，用于驱动图编辑器在“信号定义版本发生变化”时按需刷新信号节点的端口结构，而在信号未变时复用已有端口与布局。
- 与信号端口名称相关的公共约定（如统一的“信号名”端口名常量）集中在 `engine.graph.common` 中维护，校验、代码生成与 UI 层通过该约定访问端口与常量，避免在各处重复硬编码端口名或依赖中文字符串比较。

## 注意事项
- 本目录仅依赖 `engine/*` 内部模块，不得反向依赖 `app/*`、`plugins/*`、`assets/*`、`tools/*` 等上层代码。
- 不在此处引入任何 IO / UI / 资源扫描逻辑，所有能力均围绕已有的模型与视图（如 `GraphModel`、`DefinitionSchemaView`、`PackageView` 等）做纯粹的领域封装。
- 新增信号相关能力时，优先考虑放入本目录，并以清晰的服务边界暴露给其他引擎子模块，避免在各处零散地重复拼装信号特例或直接读写元数据字典。
- 为避免与 `engine.validate` 形成循环依赖，`engine.signal` 顶层不再在 import 时直接导出 `SignalValidationSuite`，改为通过模块级 `__getattr__` 延迟导入（仍保持 `from engine.signal import SignalValidationSuite` 可用）。


