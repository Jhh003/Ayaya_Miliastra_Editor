## 目录用途
统一管理离散化资源（模板、实例、节点图、战斗预设、管理配置等）的索引、读写、引用追踪与视图封装，是持久化与检索的唯一入口。

## 当前状态
- **门面编排**：`ResourceManager` 只负责对外 API 与跨服务编排；索引/图/缓存/文件操作分别委托给 `ResourceIndexService` / `GraphResourceService` / `ResourceCacheService` / `ResourceFileOps`。
- **类型规则抽离**：资源显示名与 UI 元数据提取由 `ResourceMetadataService` 统一封装，避免 `ResourceManager` 持续膨胀为条件森林。
- **节点图职责拆分**：`GraphResourceService` 仅做编排与兼容对外 API；具体实现拆为 `GraphCacheFacade`（内存+持久化缓存/失效/兼容性）、`GraphLoader`（解析+增强布局）、`GraphMetadataReader`（轻量元数据/计数兜底）、`GraphSaver`（往返校验+写盘），以及 `GraphFingerprintsService`（指纹计算复用）。
- **节点图轻量列表**：节点图列表/文件夹树等“只展示”场景应优先走 `GraphResourceService.load_graph_metadata()`：只提取 docstring 元数据；节点/连线数量优先复用 `app/runtime/cache/graph_cache` 的持久化缓存（命中且校验通过时），仍不触发解析与自动布局。
- **双层缓存**：进程内缓存由 `ResourceCacheService` 提供；磁盘持久化的节点图缓存由 `PersistentGraphCacheManager`（`persistent_graph_cache_manager.py`）管理，持久化目录位于 `settings.RUNTIME_CACHE_ROOT`（默认 `app/runtime/cache`）下，包括 graph_cache/resource_cache/node_cache 等；加载持久化图缓存时会做轻量结构一致性校验（节点/边引用与端口名匹配），不自洽视为失效并回退到重建路径。
- 持久化 graph_cache 写入前会再次确保目标目录存在，避免在“并发清缓存/外部工具清理”场景下 mkdir 后目录被删除导致写入失败。
- **代码级 Schema 缓存**：结构体/信号/关卡变量/局内存档模板等“Python 代码资源”通过各自的 `*SchemaView` 聚合并在进程内缓存；资源库刷新或外部修改这些代码资源后，需要调用对应的 `invalidate_default_*_cache()` 使视图失效并在下次访问时重新加载（例如 `update_default_template_id` 在写回局内存档模板文件后会同步失效其 SchemaView 缓存）。
- **写盘一致性**：资源索引缓存、功能包索引与运行期状态等 JSON 文件统一使用“原子写”（`atomic_json.atomic_write_json`，临时文件写完后 replace），避免异常中断导致空文件/半写入，引发索引/缓存不一致。
- **保存冲突检测（外部修改保护）**：为对齐 VSCode 等编辑器的常见策略，资源写盘支持可选的“磁盘版本（mtime）”校验：
  - `ResourceManager.save_resource(..., expected_mtime=..., allow_overwrite_external=...)`：当提供 `expected_mtime` 且检测到资源文件 mtime 已变化时，默认拒绝覆盖（返回 False），避免静默覆盖外部工具改动；显式 `allow_overwrite_external=True` 才允许覆盖。
  - `PackageIndexManager.save_package_index(..., expected_mtime=..., allow_overwrite_external=...)`：功能包索引同样支持该策略；检测到冲突时返回 False，不推进 packages.json 等派生清单写盘。
- **文件名策略单一真源**：`resource_filename_policy.py` 统一维护“保存时是否以 name 驱动物理文件名”的资源类型集合；扫描阶段的“文件名 → JSON.name 回写同步”仅对这类资源启用，其余类型允许 `name` 与文件名解耦（默认沿用 `id_to_filename_cache`），避免显示名调整触发物理文件频繁重命名。
- **资源库指纹基线**：`ResourceManager` 维护资源库指纹基线（用于缓存失效、引用追踪与 UI 自动刷新确认）。内部写盘（`save_resource/delete_resource`）会先标记指纹为脏；需要在保存链条或其它入口同步基线时，应优先使用 `ResourceManager.refresh_resource_library_fingerprint_if_invalidated()`（仅在脏标记为 True 时刷新），避免把真实外部变更“顺手吞掉”。
- **编辑期磁盘版本基线**：`PackageView/GlobalResourceView/UnclassifiedResourceView` 在反序列化模板/实例时会同步记录资源文件 `mtime` 到对象的 `_source_mtime`（运行期字段，不写入 JSON）。用于在 UI 保存时提供 `expected_mtime`，从而在外部工具已改动文件时阻止静默覆盖。
- **存档导出语义**：`PackageView.serialize()` 仅导出 `PackageIndex` 的索引型数据，不嵌入模板/实例等资源 payload；关卡实体仅通过 `PackageIndex.level_entity_id` 引用加载，不做“扫描实例并自动补写索引”的隐式回退。
- **入口收敛**：缓存/资源能力以显式实现类为入口（如 `PersistentGraphCacheManager`）；CLI/工具侧的“资源上下文构建”统一收敛到 `resource_context.py`，确保 settings 初始化与构建顺序一致。
- `resource_context.py` 支持注入应用层 `graph_code_generator` 用于节点图保存（仅 app/UI 侧需要），避免引擎层绑定代码生成策略。
- **引用追踪缓存**：节点图引用追踪器（`graph_reference_tracker.py`）在需要展示引用计数/引用详情时，会构建 `graph_id -> references` 的反向索引并按“资源库指纹”失效，避免在 UI 列表刷新中重复全量扫描全部存档/模板/实例。
- **代码生成解耦**：节点图 `.py` 源码生成不再由 `engine` 内部硬编码实现；`GraphResourceService.save_graph` 依赖注入 `graph_code_generator.generate_code(GraphModel, metadata)`，由应用层决定运行时导入/插件导入与是否注入校验逻辑。
- **文件夹结构枚举**：节点图库的“文件夹树”需要枚举磁盘上的空目录；该枚举应避免使用 `Path.rglob` 直接遍历（Windows 下遇到异常目录项可能抛错并中断），优先采用“尽力而为”的遍历策略（如 `os.walk`）。

## 注意事项
- 禁止直接拼资源路径；统一通过 `ResourceFileOps` 与 `ResourceManager`。
- 节点图仅支持类结构 Python（`.py`），位于 `assets/资源库/节点图/<server|client>/...`；列表展示不要调用 `load_resource(ResourceType.GRAPH, ...)`，否则会触发解析与自动排版。
- 不使用 try/except 吞错；发现异常直接抛出，由上层处理。
- 功能包索引（存档包索引）目录为 `assets/资源库/功能包索引/`，由 `PackageIndexManager` 负责读写；引擎与 UI 均以该目录为唯一事实来源，不要在其它目录再引入同义索引副本。
- `assets/资源库/功能包索引/packages.json` 为**派生清单**（加 `__manifest__` 与指纹），仅用于 UI/工具快速列举与保存 last_opened；当目录下 `pkg_*.json` 集合变化时会自动重建以避免清单漂移。
- `app/runtime/cache/resource_cache/resource_index.json` 为资源索引持久化缓存，包含 `__manifest__` 与 resources_fp；若版本/指纹不匹配将回退到全量扫描重建。
- 图编辑器等需要“强制从 .py 重新解析并忽略持久化 graph_cache”的场景，统一调用 `ResourceManager.invalidate_graph_for_reparse(graph_id)`（资源层：内存 + 磁盘缓存失效），上层的 GraphDataService/payload 缓存失效由应用层服务统一编排，避免 UI 侧维护“清一串缓存”的链条。
- 持久化 graph_cache 若被判定为“结构不自洽”（节点/边引用或端口名不匹配），加载阶段会将该缓存文件直接删除并回退到重建路径，避免无效缓存长期滞留导致校验与 UI 展示反复不一致。

---
注意：本文件不记录变更历史，仅描述目录用途、当前状态与注意事项。

