## 目录用途
- 存放“外围系统管理面板”的拆分子模块：三个 Tab（排行榜/竞技段位/成就）的独立 UI 组件，实现表单装配、字段读写与列表增删等交互。

## 当前状态
- `leaderboard_tab.py`：排行榜设置与榜单记录编辑。
- `rank_tab.py`：竞技段位设置与计分组编辑。
- `achievement_tab.py`：成就设置与成就条目编辑。
- 主面板 `app.ui.panels.peripheral_system_panel.PeripheralSystemManagementPanel` 负责上下文切换、所属存档多选行与统一的“数据已修改”信号发射。

## 注意事项
- 子组件仅负责就地修改传入的 `system_payload` 字典，不做持久化与业务流程；保存/写回由外层控制器统一处理。
- 不使用 `try/except` 吞错；异常直接抛出，方便定位问题。
- 组件内部通过信号 `data_updated` 告知外层“字段已变更”，外层统一更新 `last_modified` 并触发整体刷新/保存流程。

