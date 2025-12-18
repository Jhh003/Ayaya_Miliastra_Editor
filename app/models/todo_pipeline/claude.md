# Todo Pipeline

## 目录用途
承载 Todo 生成流水线的横切能力（图任务编排、调度器等），为 `todo_generator.py`
以及其它模型层模块提供可组合的服务。

## 当前状态
- `coordinator.py`：包装 `TodoGraphTaskGenerator`，集中管理节点图根任务创建、
  图名解析与图任务展开，向上游暴露无副作用的编排接口。
- `step_mode.py`：集中读取 `settings.TODO_GRAPH_STEP_MODE` 并提供语义化
  判定/描述，避免在各模块重复硬编码字符串。

## 注意事项
- 保持无 PyQt 依赖，仅强调调度逻辑。
- 引入新文件时同步更新本说明，保持实时描述。


