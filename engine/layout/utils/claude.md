## 目录用途
布局通用工具与辅助模块：承载与具体块实现解耦的公共工具函数和坐标应用逻辑。

## 当前状态
- 包含图查询与节点高度估算工具、节点复制与位置应用器、坐标分配器等模块。
- 被 `layout/internal` 与 `layout/blocks` 共同依赖，用于减少重复实现并统一行为。
- `graph_query_utils` 对纯数据节点判定和数据边索引提供共享封装，供 `LayoutContext`、flow/tree 等模块直接复用。
- `graph_query_utils` 暴露 `InputPortLayoutPlan` 以及 `build_input_port_layout_plan()`，为布局层与 UI 同步端口行数/控件换行规则；坐标分配与 UI 节点渲染都复用该计划，避免端口 Y 计算重复实现。
- `graph_query_utils` 提供 `build_event_title_lookup` 与 `resolve_event_title`，核心/块层统一从该工具解析事件标题，不再在各处维护重复逻辑。
- `graph_query_utils.collect_data_chain_paths` 返回 `ChainPathsResult`，同时接受统一的 `ChainTraversalBudget` 与调用方传入的最大链数限制，遍历与消费两侧共享同一套预算信息，定位链条截断原因更加透明；在启用 `include_skip_node_as_terminus` 时，会把跨块边界上的纯数据节点也视作链的叶子节点返回，保证这些边界节点在布局调试与链路高亮中同样具备链编号。
- `collect_data_chain_paths()` 在端口公平和限流策略外新增签名去重，避免同一链条在多输入组合下指数级膨胀；当全局配置未显式设置链路预算时，内部使用安全的默认上限，防止调试场景下配置为 0 造成无限增长。
- `collect_data_chain_paths()` 支持共享的记忆化缓存输入，布局块内的多起点可以直接复用前一次 DFS 的子问题结果。
- 数据链遍历和高度估算均可接受 `LayoutContext`，端口顺序直接走缓存而不是本地线性扫描，保证与布局结果一致。
- 节点注册表依赖通过只读 `LayoutRegistryContext` 显式注入（由 `LayoutService.compute_layout(workspace_path=...)` 或 settings 的 workspace 单一真源派生），`graph_query_utils` 不再维护任何全局可变缓存，也不再提供 `set_layout_workspace_root()` 这类隐式回退入口。
- 依赖 `engine.utils.graph.graph_utils` 判定流程端口、计算节点高度等通用图语义，保持与图工具子包的一致性。
- `data_graph_utils` 提供纯数据图的连通分量与拓扑分层结果，纯数据布局与流程树输出都直接消费这一份结构化信息。
- 纯数据图的连通分量遍历使用 `collections.deque` 的 BFS，避免列表 `pop(0)` 带来的 O(N²) 退化，整体复杂度保持线性。
- 节点高度估算由 `_estimate_node_height_from_structure` 统一实现，具体入口仅负责准备已连接端口集合。
- `basic_block_utils.build_basic_block()` 统一了 `BasicBlock` 的构造规则（节点聚合、透明度、颜色），纯数据布局与位置回写共用一套逻辑。
- `PositionApplicator` 在写回节点坐标时始终同步 `_layout_y_debug_info` 的全局 Y 值，即便 UI 未开启调试叠加也能即时显示调试图标。
- `PositionApplicator` 记录哪些节点已经在块内获取坐标，仅对仍未分配位置的原始节点使用副本坐标/调试信息做兜底同步，避免跨块复制时把本体从原块“搬”到副本所在块；BasicBlock 转换阶段按 `LayoutBlock.flow_nodes + LayoutBlock.data_nodes` 生成块节点集合，并对副本节点按 `copy_block_id` 做归属过滤，避免同一副本在多个块中重复出现。对于“仅由输出引脚消费”的尾部纯数据链，归属由 `GlobalCopyManager` 的兜底挂载与块内数据放置器的覆盖放置共同保证；目标块选择按“尾部链与外部相连的边界节点中最靠右的块（column_index 最大，与块间排版一致）”确定，以避免出现回头线。
- `node_copy_utils` 提供数据节点复制的基础工具函数：`create_data_node_copy()` 以"根原始节点 ID + 块 ID + 计数器"生成副本；`collapse_duplicate_data_copies()` 合并重复副本；`remove_data_nodes()` 批量移除节点。复杂的复制逻辑已移到 `GlobalCopyManager`；副本身份解析类逻辑统一由 `copy_identity_utils` 作为单一真源提供。
- `global_copy_manager` 提供 `GlobalCopyManager` 类，在所有块识别完成后统一分析跨块共享的数据节点，批量创建副本并重定向边；取代原有"边识别边复制"的逻辑。复制执行阶段保持“纯计划 → 应用”的结构，其中应用流程拆分为：确保副本节点存在、原地重定向边、补齐输入边、边去重，便于独立测试与排查。
  - **复制规则**：(1) 同一块内的数据节点不复制；(2) 非 owner 块内的数据连线会被重定向到副本；(3) 同一块内多个消费者共用一个副本；(4) 重复执行保持幂等，优先复用已存在副本。
  - **核心方法**：`analyze_dependencies()` 生成 `CopyPlan`；`build_application_plan()` 输出纯数据的 `GlobalCopyApplicationPlan`；`apply_application_plan()` 执行计划（创建缺失副本、原地重定向既有边、补齐副本输入边），并保证边 ID 可复现（不使用 uuid）。
  - **查询接口**：`get_block_data_nodes()` 查询每个块应放置的数据节点集合；`get_block_copy_mapping()` 获取块内副本映射；`get_block_owned_nodes()` 获取块拥有的原始节点。
- `edge_index_proxies.CopyOnWriteEdgeIndex` 提供延迟克隆的边索引代理，块识别与复制逻辑可共享该容器减少大图复制。
- `copy_identity_utils` 提供副本节点的身份解析单一真源：副本识别、canonical original 解析、copy_block_id 推断、块序号/计数器解析与副本排序（rank）等，供 `LayoutService`、`PositionApplicator` 与复制管理器复用，避免重复实现与兼容性分叉。
- `CoordinateAssigner` 作为协调入口，负责基于 `BlockLayoutContext` 调用 X/Y 轴规划器，为当前块内所有节点写入最终坐标与调试信息。
- `coordinate_assigner_x` 模块封装流程与数据节点的列索引计算逻辑：先利用 `longest_path.resolve_levels_with_parents` 计算流程节点的最长路径列索引，再根据数据链的消费者位置向左回溯为数据节点分配列索引，并对缺少链信息的节点使用 `node_slot_index` 回退列。
- `coordinate_assigner_x` 对“缺少链信息（未被任何数据链引用）”的纯数据节点，会基于块内纯数据边的拓扑层级分配回退列索引（仍位于流程列右侧），保证同块内数据边尽量从左到右，减少回头线；若不存在可用拓扑约束则回退为稳定递增分配。
- `coordinate_assigner_data` 模块提供数据节点坐标规划器 `DataCoordinatePlanner`，通过 `DataNodePlacementPlan`、`DataNodeYDebugSnapshot` 等 dataclass 将“列内排序 + Y 轴决策”与 `context` 写回解耦，并以显式注入的 `slot_width` 与预计算列索引组合得到最终 X 坐标，支持多输出中点、右对齐、链条端口距等候选策略的组合。
- `data_y_relaxation` 模块提供 `DataYRelaxationEngine`：在完成一次性坐标规划后，对块内纯数据节点的 Y 轴做少量迭代松弛，使多父合流/多子分叉节点更接近邻居中心，同时通过“下界 + 不重叠”投影保持硬约束；可通过 `settings.LAYOUT_RELAX_DATA_Y_IN_BLOCK` 开关启用/关闭。
- `DataYRelaxationEngine` 支持块内数据节点 Y 的“紧凑偏好”：当 `settings.LAYOUT_COMPACT_DATA_Y_IN_BLOCK` 启用时，会在松弛目标阶段把“相对硬下界可上移余量很大”的节点向下界方向拉近（由 `LAYOUT_DATA_Y_COMPACT_PULL` 与 `LAYOUT_DATA_Y_COMPACT_SLACK_THRESHOLD` 控制），以减少垂直空洞；最终仍由“下界 + 不重叠 + 多父区间”投影保证硬约束不被破坏。
- `DataYRelaxationEngine` 额外对“跨列的一对一链路”（子节点仅有一个父节点）启用更强的邻居对齐，使成对节点更贴近，减少边交叉/回折（同样受下界与不重叠约束保护）。
- `DataYRelaxationEngine` 对“多父合流”节点增加了父节点区间夹紧：目标节点中心会被限制在父节点中心的[min,max]区间内（仍受列内不重叠与下界投影保护），以满足“被连节点应位于多父节点之间”的观感预期；实现上会将“父中心区间”转换为目标节点 `top_y` 的可行区间（减去目标节点高度的一半）以便直接参与列内投影。
- `DataYRelaxationEngine` 在构建纯数据邻接关系时会按目标节点 ID 去重，避免“同一对节点的多条数据边（多端口连接）”被误判为多子分叉而放大累计高度，导致同块内出现巨大 Y 空洞。
- `DataYRelaxationEngine` 的列内投影会保留“链 ID（升序）→堆叠提示→松弛目标”的优先级顺序：同列先按链编号固定上下关系（chain_id 越大越靠下），再按 `node_stack_order` 保持链内堆叠提示，避免松弛阶段因 `preferred_y` 重新排序导致同列节点换位。
- 数据节点坐标计算遵循“先纯计算计划、再统一写回”的约定，`CoordinateAssigner` 仅负责将规划结果写入 `node_local_pos`、`debug_y_info` 等结构，便于单元测试与后续策略替换。
- `BlockLayoutContext` 内置节点高度缓存，`CoordinateAssigner`、`DataNodePlacer`、`BlockBoundsCalculator` 等模块统一复用，减少重复估算。
- `graph_query_utils.build_edge_indices` 为布局/块上下文提供共享的流程与数据边索引，减少重复扫描并保持缓存语义一致。
- `graph_query_utils.collect_upstream_data_closure` 支持按需忽略 skip 集合，供跨块数据复制时获取完整上游闭包，避免副本缺失输入。
- `graph_query_utils.has_flow_edges` 利用 `is_flow_edge` 的宽松判定规则识别流程边，只要目标端口被识别为流程输入（如“流程入/是/否/默认/循环体/循环完成/跳出循环”）或源端口名称符合流程输出约定，即视为存在流程连线，确保仅含流程入口/出口而无显式事件节点的图也能被正确标记为“包含流程”，避免在布局与流程树中被误归类为纯数据图。
- 纯算法类工具（如最长路径、坐标规划）优先在本目录集中维护，调用方通过 `engine.layout` 的上层服务类进行访问。

## 注意事项
- 工具函数应保持无副作用或副作用可控，不直接修改全局状态。
- 新增工具时优先考虑是否可以复用现有图工具子包（如 `engine.utils.graph`、`engine.utils.text`），避免逻辑散落。
- 维持坐标策略对象的纯函数特性，先生成计划再写入 context，调试记录需通过专门的数据结构传递。
- 功能若可作为公共算法（如数据图分层、链遍历），应优先落在本目录集中维护。


