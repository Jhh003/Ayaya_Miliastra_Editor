## 目录用途
节点图布局层（纯逻辑）：识别与排布基本块，枚举行内/跨块数据链，计算节点坐标与块矩形，并生成可选的布局调试信息；对 UI 与资源保持解耦，仅输出结构化数据。

## 当前状态
- 根目录仅保留 `__init__.py` 用于导出稳定 API，当前对外导出 `LayoutService`、`generate_flow_tree`、`LayoutContext`、`invalidate_layout_caches` 与布局常量；实际实现位于：
  - `internal/`：`LayoutService`、上下文与常量（核心算法入口为内部实现，不作为包级 API 导出）；
  - `blocks/`：块识别、块内布局、链条枚举与定位；
  - `flow/`：事件根发现、流程树生成与布局前预处理；
  - `utils/`：坐标分配、节点复制、图查询与结果写回；跨块数据节点复制在收尾阶段通过边重定向工具保持幂等，当前不在布局阶段主动删除“疑似孤立”的数据副本节点，以避免在索引与 `model.edges` 不完全同步时写出结构不自洽的缓存。BasicBlock 与 `_layout_blocks_cache` 视图只按 `copy_block_id` 将数据副本归属于单一块，但 Y 轴调试信息会把同一原始数据节点及其副本的链路明细汇总到一起，保证点击任一版本都能看到完整链路。
- 子模块统一复用 `engine.utils.graph` 子包（如 `graph_utils`）暴露的图语义工具，避免在布局层维护重复规则。
- 包级 API 通过 `engine.layout` 统一导出 `LayoutService`、布局常量与 `generate_flow_tree`，供 UI / 测试直接使用。
- `LayoutService` 在克隆模型上执行布局后，会将 `_layout_block_relationships`、`_layout_blocks_cache` 与 `_layout_cache_signature` 回写到调用方模型，供流程树等功能直接复用且可做签名一致性校验。
- `LayoutContext` 统一缓存端口索引、边集合及事件元数据；`LayoutContext` 的缓存复用基于“结构签名”校验（而非仅按对象引用），避免模型变更后复用过期索引导致幽灵问题。
- 块列索引与流程槽位的最长路径计算通过 `utils.longest_path.assign_longest_path_levels` 共享实现，保持拓扑排序、循环回退与稳定排序策略一致。
- 纯数据图布局在调用方未传入上下文时会自动构建 `LayoutContext`，始终让节点高度与数据边统计从缓存获取，避免退回到 O(N·E) 的全图扫描。
- 根目录不再保留单独门面模块，所有公共入口都应从 `engine.layout` 包级导出获取，避免重新引入重复文件。

## 注意事项
- 严禁依赖 UI、外设 I/O 或 `app/*`、`plugins/*`、`assets/*`，必要信息通过参数注入（如 `node_library`、全局设置）。
- 布局算法需可复现（相同输入得到相同输出）；链枚举以“消费者流程节点的输入端口”为视角回溯上游纯数据节点，遇到流程口仅作为起源标记，并在跨块复制场景下避免语义等价的重复链条。
- 逻辑类文件放入对应子包，根目录新增文件需先评估是否应在现有子包内实现。
