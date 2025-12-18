# Server 事件节点目录

## 目录用途
- 服务器侧事件节点定义，一节点一文件，对应运行期触发点（定时器、背包、实体、巡逻等）。
- 事件函数只负责调度同一事件流中的后继节点，不直接执行复杂业务。

## 当前状态
- 由静态注册器纳入 `plugins.nodes.server`，供 `from plugins.nodes.server import *` 统一导入。
- 节点函数均使用 `@node_spec` 描述端口，依赖共用 helper 位于 `plugins/nodes/shared`.
- 信号相关事件节点 `监听信号` 通过一个字符串输入端口“信号名”选择要监听的信号，并在引擎信号系统提供的参数定义基础上，在 UI 中为每个信号参数自动追加对应的数据输出端口。

## 注意事项
- 保持文件名与事件名称一致，便于查找与生成文档。
- 不要在事件节点里导入 UI 层或自动化模块，仅依赖 `engine` 与 `plugins.nodes.shared`.
- 输出日志统一通过 `engine.utils.logging.logger`.


