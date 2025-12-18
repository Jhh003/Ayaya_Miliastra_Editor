# Client 执行节点目录

## 目录用途
- 客户端执行节点集合，涵盖镜头、输入、局部状态修改等可在客户端完成的动作。
- 每个文件实现一个 `@node_spec` 节点函数。

## 当前状态
- 通过静态注册表导出，运行时由 `plugins.nodes.client` 统一导入。
- 共享逻辑位于 `plugins.nodes.shared.client_执行节点_impl_helpers`（如有）。

## 注意事项
- 不访问服务器专属 API，必要的 RPC 交给节点自身或 shared helper。
- 日志输出统一走 `engine.utils.logging.logger`。
- 若节点需要界面交互，保证只调用允许的 UI 抽象接口。


