## 目录用途
`app/runtime/services/` 存放 **无 PyQt6 依赖** 的应用层运行时服务（service），用于收敛“资源加载 / 缓存策略 / 领域计算”等可测试逻辑，供 UI 控制器与面板复用。

## 当前状态
- `graph_data_service.py`：图数据统一门面（GraphDataService）
  - 统一提供 `GraphConfig/graph_data/GraphModel` 的加载与内存缓存（含 GraphModel 的签名失效，避免布局变更后复用旧模型）
  - 桥接进程内 `graph_data_key` payload 缓存（resolve/store/drop/clear），并将 `invalidate_graph()` 作为“一句清干净”的统一失效入口，供 Todo/预览/导航共享
- `graph_model_cache.py`：GraphModel 缓存工具（纯函数 + 小型 entry），供图相关 UI 在本地字典缓存 GraphModel 时复用
- `json_cache_service.py`：运行期 JSON 缓存门面（JsonCacheService）
  - 统一派生 runtime_cache_root（遵循 `settings.RUNTIME_CACHE_ROOT` 与 `engine.utils.cache.cache_paths` 单一真源）
  - 提供“整文件 JSON”读写与“KV（schema_version + values）”模式，供 UI 会话状态与轻量 UI 记忆类缓存复用
  - 写入统一采用原子写（tmp -> replace），避免中断导致空文件/半写入
  - 提供 `append_jsonl/append_text`，用于“回放记录”等按行追加的落盘场景，避免各处手写路径拼接与文件打开逻辑

## 依赖边界
- 允许依赖：`engine/*`、`app/runtime/*`、`app/common/*`
- 禁止依赖：`app/ui/*`、`PyQt6/*`

## 注意事项
- 本目录的服务必须保持可单测：不要在导入阶段访问磁盘或启动线程，不要依赖 Qt 对象生命周期。
- 缓存失效应提供明确入口（按 graph_id 与全量清理），避免 UI 侧维护“需要清一串缓存”的链条。

