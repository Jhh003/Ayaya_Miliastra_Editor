# 流程控制节点（server）

## 目录用途
存放服务器侧“流程控制节点”的实现与规范声明（`@node_spec`）。本目录下的节点负责基于布尔/多分支等条件在不同流程路径间进行分流与控制。

## 当前状态
- 节点声明通过 `engine.nodes.node_spec.node_spec` 提供，类型为中文端口类型（推荐通过 `from engine.nodes.node_spec import node_spec` 导入）。
- 与实现层解耦：节点解析以 AST 扫描 `@node_spec` 为唯一权威来源（不导入模块）。

## 注意事项
- 布尔类型统一命名为“布尔值”（输入/输出/参数一律使用该名称），避免与“布尔”混用导致类型校验不通过。
- 仅声明“流程/数据”端口的类型，不在实现中做名称硬编码判断；流程端口的 UI/验证判定统一走 `engine.nodes.port_type_system.is_flow_port_with_context()`。
- 严格遵循“只解析不导入”的规则；实现中的副作用（如日志）不会影响解析与索引构建。
- 当流程节点的泛型数据端口只接受部分类型（如控制表达式只支持整数/字符串），需在 `@node_spec` 中配置 `input_generic_constraints`，以便检测器能够阻止不合法的连接或常量。


