# Server 查询节点目录

## 目录用途
- 集中声明服务器侧“查询类”节点：读取仇恨值、背包、装备、环境配置、路径点等。
- 每个节点函数返回计算或查询结果供后续节点使用。

## 当前状态
- 所有节点以 `@node_spec` 定义端口，必要的常用逻辑放入 `plugins.nodes.shared.server_查询节点_impl_helpers`。
- 由静态注册表暴露给 `plugins.nodes.server`.

## 注意事项
- 查询节点只读状态，不在内部修改 GraphModel 或运行态数据。
- 输出日志统一走 `engine.utils.logging.logger`，避免私有 print。
- 共通格式化/校验逻辑尽量抽到 shared helper，保持节点文件简洁。
- 字典查询节点的字典端口统一使用“泛型字典”端口类型；键端口通过 `input_generic_constraints` 声明仅接受实体、GUID、整数、字符串、阵营、配置ID、元件ID，值相关输出端口不允许字典类型，约束列表中也不要放入泛型或泛型列表。


