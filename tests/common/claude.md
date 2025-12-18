## 目录用途
存放 app/common 这类“跨 UI/模型共享的轻量模块”相关测试，重点回归缓存/协议等全局一致性规则。

## 当前状态
- `test_in_memory_graph_payload_cache_contract.py`：回归 `in_memory_graph_payload_cache` 的 cache_key 规则、解析优先级与失效语义。

## 注意事项
- 保持纯逻辑，不引入 PyQt6 与重型引擎依赖。
- 不使用 `try/except` 吞错，失败直接抛出由 pytest 记录。


