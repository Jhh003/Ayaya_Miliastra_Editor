## 目录用途
`engine/graph/models/` 存放节点图与资源视图相关的核心数据模型与序列化逻辑，包括 `GraphModel`、`PackageModel` 及实体/模板等辅助模型，不包含具体节点实现或 UI 代码。

## 当前状态
- 图模型：`graph_model.py` 定义图结构与端口/边/基础块等数据结构，配合 `graph_serialization.py` 与 `graph_hash.py` 实现序列化与内容哈希。
- 语义元数据（`signal_bindings` / `struct_bindings`）采用“单一写入阶段”：除 `engine.graph.semantic.GraphSemanticPass` 外禁止任何模块直接写入对应 metadata；稳定 ID 通过节点隐藏常量 `__signal_id` / `__struct_id` 作为锚点，Pass 会按需回填；`GraphModel.set_node_signal_binding/set_node_struct_binding` 等直接写入接口视为废弃并禁止使用。
- 图连线缓存：图模型内部维护 `edges_revision`（连线变更版本号），供依赖 edges 的索引缓存可靠失效；当外部直接原地修改 `GraphModel.edges` 或 `EdgeModel` 字段时需调用 `touch_edges_revision()` 触发失效。
- 存档模型：`package_model.py` 定义模板/实例/战斗预设/管理配置等存档侧数据类型，供 `engine.resources` 与上层应用复用。
- 实体模板：`entity_templates.py` 以 `engine.configs.rules.entity_rules.ENTITY_TYPES` 为唯一规则来源，集中维护 UI 展示用的实体类型元数据与变量/组件类型列表；其中“规范中文变量类型”由 `engine/type_registry.py` 作为唯一事实来源（避免 UI/验证/结构体/端口多处清单漂移），并通过 `get_entity_type_info` 等函数为元件库、实体摆放等页面提供统一的实体类型图标与说明。
- 关卡变量：`package_model.py` 中提供 `LevelVariableDefinition`，用于在管理配置的代码资源中集中声明关卡变量并按 ID 引用。

## 注意事项
- 保持纯数据与纯逻辑，不在本目录中引入 PyQt 或磁盘 IO；需要访问资源或 UI 时由上层模块通过模型实例协作完成。
- 涉及实体/变量/组件类型时，应与 `engine.configs.rules` 与 `engine.configs.components` 中的规则和注册表保持语义一致，避免在本目录重复维护规则副本。
- 本文件不记录修改历史，只描述“目录用途、当前状态、注意事项”的实时概况。

## 目录用途

`engine/graph/models/` 目录集中存放图模型与存档相关的数据结构，包括：
- 图结构模型与序列化/哈希所需类型；
- 存档中模板/实例/战斗预设/管理配置的配置类型；
- 实体类型与 UI 展示信息（图标、默认节点图等）以及辅助查询函数。

## 当前状态

- `graph_model.py`、`graph_serialization.py`、`graph_hash.py`、`graph_config.py` 提供图的结构化表示、序列化与内容哈希能力。
- `package_model.py` 定义了 `TemplateConfig` / `InstanceConfig` / `ComponentConfig` 等存档层配置类型。
- `entity_templates.py` 作为实体类型与组件类型的 UI 入口，基于 `engine.configs.rules.entity_rules` 与通用组件注册表提供 `ENTITY_TYPES`、`VARIABLE_TYPES` 以及 `get_all_component_types()` 等查询函数，其中组件类型列表由 `engine.configs.components.component_registry` 统一提供，保证与规则与 UI 一致。

## 注意事项

- 本目录仅包含纯数据模型与无副作用的辅助函数，不引入 PyQt 或 UI 依赖。
- 关于实体与组件的规则（可用组件、挂载限制等）应从 `engine.configs.rules` 读取，避免在此处复制规则逻辑。
- 在为 UI 提供快捷查询函数时，保持返回值与规则模块中使用的实体/组件名称完全一致，避免出现多套命名。

---

注意：本文件不记录任何修改历史。请始终保持对"目录用途、当前状态、注意事项"的实时描述。

## 目录用途
- 图模型与关联数据结构、序列化、哈希与配置等纯逻辑定义的集合，仅包含无 I/O 的数据与算法，不依赖应用层或插件层。

## 当前状态
- 提供 `GraphModel` / `NodeModel` / `EdgeModel` / `PortModel` / `BasicBlock` 等核心数据结构。
- 稳定哈希与语义辅助逻辑统一依赖 `engine.utils.graph.graph_utils` 中的工具函数，避免重复维护。
- 提供序列化 / 反序列化与稳定哈希计算，并通过 `GraphConfig` 承载独立的节点图资源。
- 节点图序列化格式保持单一：`nodes/edges` 使用列表结构，节点坐标字段为 `pos`，端口列表为 `list[str]`，连线字段为 `src_node/src_port/dst_node/dst_port`。
- 实体类型 UI 显示信息与规则聚合视图（规则来源于规则子系统）；`ENTITY_TYPES` 字典同时包含真实实体类型（从 `ENTITY_RULES` 导入）和 UI 扩展分类（元件组、掉落物），便于 UI 层统一获取图标和元信息。
- 节点图变量以字典列表形式挂在 `GraphModel.graph_variables` 上，字段结构与 `GraphVariableConfig.serialize()` 对齐，支持基础类型、列表、结构体，以及字典变量的“键/值数据类型”元数据（通过 `dict_key_type` / `dict_value_type` 记录字典内部键和值的中文类型名）。
- 序列化结果完整记录跨块复制元信息（`is_data_node_copy` / `original_node_id` / `copy_block_id`），并在反序列化时根据约定自动回填，旧缓存不会把副本误判为原始节点。
- 克隆策略：`GraphModel.clone` 采用选择性复制与结构重建，节点和连线按字段重建，`event_flow_*` 与 `basic_blocks` 使用浅复制创建新容器，`graph_variables` 与 `metadata` 则保持深拷贝以避免共享可变状态。

## 注意事项
- 不做外设 I/O（文件 / 网络 / GUI）；文本与持久化由上层负责。
- 跨子模块引用使用 `engine.graph.models.*` 明确路径，避免循环依赖。
- 新增或调整模型字段时需同时更新序列化 / 反序列化和克隆逻辑；本项目不承诺旧序列化格式与旧缓存文件长期可用，结构变更后应通过清缓存或迁移脚本处理存量数据。

