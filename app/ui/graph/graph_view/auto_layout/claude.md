目录用途：存放 GraphView 自动排版流程代码（验证、布局、差异回填）。
当前状态：AutoLayoutController 负责按钮入口；验证失败时会弹出 Toast 提示首条错误并提示在“设置>自动排版”开启“图编辑器详细日志”查看详情，若 settings.GRAPH_UI_VERBOSE 为 True 仍在控制台打印完整错误；布局计算调用 `LayoutService.compute_layout` 时会显式传入 `workspace_path` 以保证注册表/布局规则来源稳定。
注意事项：调用需传入 GraphView 场景；复合节点自动排版依赖 composite_edit_context 提供 manager 与 composite_id 以构建虚拟引脚映射。
