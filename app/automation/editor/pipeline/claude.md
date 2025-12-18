## 目录用途
- `editor_exec_steps` 的“通用编排管线”拆分目录：将**步骤计划表 / 识别预热 / 视口同步 / 缓存失效 / 回放记录**等横切关注点从大文件中抽离。

## 当前状态
- `step_plans.py`：集中定义 graph_* 步骤的计划表（step_type → plan）与轻量 handler 绑定（handler 仅做业务委托）。
- `recognition_prewarm.py`：连线前的识别预热（基于 executor 的 view token 判断是否需要刷新）。
- `viewport_sync.py`：单步模式下的“可见节点坐标同步”（视口 token 变化才触发）。
- `cache_policy.py`：步骤前后缓存失效策略（连线链上下文、视觉缓存、场景快照）。
- `replay_recorder.py`：关键步骤输入输出落盘（JSONL + 可选截图），用于回归定位与离线复现。

## 注意事项
- 本目录只做编排/策略/记录，不直接实现节点创建/连线/配置等业务；业务逻辑在 `editor_nodes.py` / `editor_connect.py` / `config/*` 中。
- 不在此层新增吞异常的 `try/except`；落盘失败应直接抛错暴露环境问题。
- 所有落盘路径统一从运行时服务派生：优先使用 `app.runtime.services.json_cache_service.JsonCacheService`（遵循 `settings.RUNTIME_CACHE_ROOT`），默认在 `app/runtime/cache` 下。

---
注意：本文件不记录任何修改历史。请始终保持对「目录用途、当前状态、注意事项」的实时描述。


