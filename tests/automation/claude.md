## 目录用途
存放 automation（自动化执行/协议约束）相关测试，重点回归“协议契约不漂移、跨模块依赖不退回到具体实现类”。

## 当前状态
- `test_executor_protocol_contract.py`：反射级校验 `EditorExecutorProtocol/ViewportController` 的关键方法签名与实现一致，并约束关键模块使用协议类型注解。

## 注意事项
- 测试应尽量避免依赖真实窗口/截图/输入环境；优先做契约级与纯逻辑回归。
- 不使用 `try/except` 吞错，失败直接抛出由 pytest 记录。


