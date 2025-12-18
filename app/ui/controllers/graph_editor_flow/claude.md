## 目录用途
`ui/controllers/graph_editor_flow/` 承载“节点图编辑器”的纯流程服务（load/save/validate/auto_layout_prepare）与会话状态机，把跨域链路从 `GraphEditorController` 中拆出去，降低 God Object 体积与多人协作冲突面。

## 当前结构
- `session_state_machine.py`：编辑会话状态机（单一真源），统一派生 `save_status` 与 `EditSessionCapabilities`，避免 controller/view/scene 之间语义分叉
- `load_service.py`：加载管线服务（反序列化 → 复合节点端口同步 → **GraphSemanticPass 对齐语义元数据** → 场景替换 → 批量装配 → 信号端口按需同步 → 小地图修复）
- `save_service.py`：保存流程服务（序列化 → ResourceManager.save_resource → 回读确认）
- `validate_service.py`：验证流程服务（ComprehensiveValidator.validate_graph_for_ui，生成 UI 可用 issues 列表）
- `auto_layout_prepare_service.py`：自动排版前准备服务（按需强制重解析/持久化缓存 payload 构建）
- `new_node_ports_policy.py`：新建节点“初始端口策略”（纯逻辑、可单测），集中维护节点创建时的业务特例（如“拼装字典”默认键值对端口）

## 注意事项
- 本目录服务不直接发射 Qt 信号；与 UI 的交互/提示由 `GraphEditorController` 统一处理。
- 不在 service 内做 try/except；遇错直接抛出，由上层统一处理。
- 会话能力与保存状态必须走 `session_state_machine`，禁止在 controller/view/scene 复制 bool 字段造成分叉。
- 节点创建的“默认端口/预置值”等业务规则必须集中在本目录的纯逻辑策略中；禁止在 controller/scene/view 内按节点名硬编码 if/else。


