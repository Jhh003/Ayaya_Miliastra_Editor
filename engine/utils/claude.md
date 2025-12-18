# Utilities 模块

## 目录用途
提供通用工具与基础设施能力，供 UI 与核心逻辑复用。根据语义拆分为若干子包：
- `graph`：图结构算法与节点图数据处理工具（事件分组、拓扑排序、端口判定等）。
- `logging`：统一日志接口与控制台输出清洗工具。
- `cache`：运行时缓存路径与邻域指纹等通用缓存辅助工具。
- `undo`：纯模型层的撤销/重做命令系统（通过 `engine.utils` 顶层延迟导出）。
- `text`：文本相似度与中文近似匹配等通用文本工具。

根目录仅提供：
- `name_utils.py`：命名与文件名规范工具，包含：
  - 标识符/类名/节点文件名清洗：`make_valid_identifier` / `sanitize_class_name` / `sanitize_node_filename`
  - Windows 文件名清洗：`sanitize_windows_filename` / `sanitize_resource_filename` / `sanitize_package_filename` / `sanitize_composite_filename`
  - 通用“唯一名称”生成：`generate_unique_name(base_name, existing_names, separator="_", start_index=1)`，用于在 UI 或引擎层根据已有名称集合生成如 `名称` / `名称_1` / `名称_2`… 等不重复名称
  - 顺序去重小工具：`dedupe_preserve_order(items)`，在保持首次出现顺序的前提下对任意可哈希元素序列做去重，供端口类型推断、事件流任务与 Graph Code 解析等模块统一复用，避免在各处手写 `dict.fromkeys` 或 `seen` 集合逻辑
- `__init__.py`：延迟导出 `UndoRedoManager` / `Command`，其余功能请直接从子包导入。

## 子包结构
- `graph/`：`graph_algorithms.py`、`graph_utils.py`、`node_defs_fingerprint.py`。
- `logging/`：`logger.py`、`console_sanitizer.py`。
- `cache/`：`cache_paths.py`、`fingerprint.py`。
- `undo/`：`undo_redo_core.py`。
- `text/`：`text_similarity.py`。

统一从子包导入具体工具函数或类：
- `from engine.utils.graph.graph_utils import is_flow_port_name`
- `from engine.utils.logging.logger import log_info`
- `from engine.utils.cache.cache_paths import get_runtime_cache_root`
- `from engine.utils.undo.undo_redo_core import UndoRedoManager`
- `from engine.utils.text.text_similarity import chinese_similar`

## 注意事项
- 工具层不依赖 UI、不直接做外设 I/O，仅依赖标准库与 `engine/*` 内部模块。
- 严格避免循环依赖；需要跨子模块协作时通过清晰的接口函数或类实现。
- 工具层函数不使用 `try/except` 吞没错误，异常应直接抛出，由上层显式处理。

---
注意：本文件不记录任何修改历史。请始终保持对“目录用途、当前状态、注意事项”的实时描述。


