## 目录用途
- 存放存档级综合校验规则（Comprehensive Rules），包括关卡实体、模板/实例挂载关系、管理配置、信号系统、结构体系统、资源库节点图等高层规则。
- 这些规则基于 `ComprehensiveValidator` 与 `ValidationPipeline` 运行，聚焦“包级/资源级一致性”，不处理节点图源码的语法与代码风格。
- 信号系统相关规则对外稳定入口为 `signal_rule.py`，其实现已拆分到 `signal/` 子包；结构体系统相关规则集中在 `struct_rule.py` 中，检查结构体节点绑定的结构体 ID 与字段名是否与当前结构体定义保持一致。

## 当前状态
- 已实现的规则涵盖信号使用一致性（存在性、参数列表、常量类型与连线类型）、结构体节点绑定与字段一致性、关卡实体/模板/实例挂载约束、管理配置完整性、资源库节点图合法性以及复合节点结构检查等。
- 规则通过 `build_rules(validator)` 统一注册，运行时会从 `validator` 上获取 `package`、`resource_manager`、`node_library` 等上下文信息。

## 注意事项
- 本目录中的规则只能依赖引擎层模块（`engine.*`），禁止反向依赖应用层或插件层（`app.*` / `plugins.*` / `assets.*` / `tools.*`）。
- 新规则应尽量聚焦“图外/包级”问题，避免与 `engine.validate.api.validate_files` 中的 M2/M3 源码规则重复。
- 在设计类型相关规则时，需遵守端口类型系统约定：基础类型、列表类型与“泛型家族”（如“泛型”“泛型列表”“泛型字典”）需要在规则中保持一致的判定逻辑，以避免产生误报。

## 目录用途
- 拆分自 `ComprehensiveValidator` 的功能包级规则实现集合。
- 每个文件聚焦单一领域（关卡实体、模板、实例、UI、复合节点等），提供 `BaseComprehensiveRule` 子类与协作函数。
- 通过 `build_rules()` 返回规则列表供 `ValidationPipeline` 顺序执行。

## 当前状态
- 规则逻辑按领域拆散，便于理解与维护；共用 `validator` 注入的上下文（package、resource_manager、graph 校验入口）。
- Graph 结构与端口检查由 `engine/validate/comprehensive_graph_checks.py` 统一提供，rule 代码只负责装配与业务判断；共享快照缓存通过 `helpers.get_graph_snapshot` 暴露，避免在多个规则中重复标准化节点/连线。
- `BaseComprehensiveRule` 统一在 `apply()` 中注入新增问题，子类仅需实现 `run(ctx)` 并返回 `ValidationIssue` 列表；若 `run()` 内部调用 `validator.validate_graph_*`，可以直接合并其返回的增量问题。
- `helpers.py` 提供模板/实例/关卡节点图迭代器、组件兼容性与 EngineIssue→ValidationIssue 的转换工具，模板类型校验、前端变量规则、图性能与复用性规则以及信号系统与结构体系统规则等共用的细粒度逻辑在各自模块内集中封装，避免多处硬编码与重复扫描。
- `helpers.convert_engine_issues_to_validation(...)` 会尽量保留 `code/file/graph_id/node_id/line_span` 等字段，并将规则侧的 `detail` 合并进 UI 侧的 detail，保证错误码与定位信息在上层展示/跳转时不丢失。
- 部分规则会结合 `PackageIndex` 与包级视图，检查存档与模板/实例/节点图之间的资源归属和引用闭合情况，例如关卡实体是否存在、实例模板是否有效以及存档索引中的节点图是否与实体挂载关系一致。

## 注意事项
- 规则实现禁止互相引用 UI 层；仅依赖 `engine.*` 内部模块。
- 若新增规则，请创建独立模块，继承 `BaseComprehensiveRule` 并在 `__init__.py` 的 `build_rules()` 中注册顺序。
- 规则应返回 `ValidationIssue` 列表，不记录历史，只描述当前目录用途与约束。
- 需要执行图校验时统一通过 `ComprehensiveValidator` 的公开接口（如 `validate_graph_data`、`validate_graph_ports` 等）触发，避免直接访问私有下划线方法。

