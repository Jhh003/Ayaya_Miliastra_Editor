# App/Common

## 目录用途
存放可被 `app.models` 与 `app.ui` 共享的轻量级工具模块，确保无 PyQt 依赖，用于封装跨层通用的数据结构与缓存。

## 当前状态
- `in_memory_graph_payload_cache.py`：**进程内临时**的节点图 payload（`graph_data`）缓存，提供按图根 ID/图 ID 组合键存储、基于 `detail_info` 的解析入口（`graph_data`/`graph_data_key`），以及按图根/按图 ID/全量清空的失效函数；应用层统一通过 `app.runtime.services.graph_data_service.GraphDataService` 桥接，避免多入口读写/失效导致分叉。
- `__init__.py`：占位以声明 Python 包。

## 注意事项
- 保持纯 Python 与轻量依赖，不得引用 UI/引擎中的重型组件。
- 模块需关注线程安全（缓存默认使用锁保护），并提供显式的清理/失效入口避免内存泄漏与布局更新后缓存失步。
- `app/ui` 与 `app/models` 不应直接 import 本模块；如需读写/失效，请走 `GraphDataService`。
- 本目录描述仅聚焦“用途/状态/注意事项”，不记录操作历史。

