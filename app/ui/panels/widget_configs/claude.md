## 目录用途
`ui/panels/widget_configs/` 存放 UI 控件类型化配置面板的实现，拆分为基类/共享字段部件以及按控件类型划分的子模块，避免再把所有配置写在单一文件里。

## 当前状态
- `base.py`：提供 `BaseWidgetConfigPanel`、字段绑定工具，以及 `WidgetConfigForm`、`VariableSelector` 等可复用输入部件。
- `interaction_controls.py`：交互类控件（交互按钮、道具展示）所需的配置面板，支持按键映射、次数限制以及文件对话框选择图标资源。
- `textual_panels.py`：文本框、弹窗等文本展示类控件的配置；文本框允许一键插入变量占位符，弹窗按钮支持增删改并写回配置字典，涉及变量名或按钮配置等临时输入统一通过 `app.ui.foundation.input_dialogs` 提供的标准化输入对话框完成，按钮编辑弹窗基于 `BaseDialog` 统一构建，保持与其它表单对话框一致的布局与按钮语义；按钮列表支持工具条“添加/移除”按钮，并在列表上提供右键菜单“删除当前行”以快速移除当前选中按钮。
- `status_panels.py`：进度条、计时器、计分板等状态类控件。
- `selection_panel.py`：卡牌选择器配置，内置列表管理（添加/编辑/移除）并将卡牌元信息写入 `settings["cards"]`；卡牌列表同样提供右键菜单“删除当前行”，与按钮配置与其它列表类面板保持一致的删除交互，卡牌编辑弹窗同样基于 `BaseDialog` 统一骨架构建。
- `registry.py`：集中维护控件类型到面板类的映射，并向旧接口 `create_config_panel` 暴露。

## 注意事项
- 新增控件类型时，应在对应子模块中实现面板，并在 `registry.py` 注册；尽量复用 `WidgetConfigForm` 的字段助手与变量选择器，保持交互一致。
- 如需额外的复合输入部件，请添加到 `base.py`，不要在各个面板内重复造轮子。
- 所有面板仍通过 `BaseWidgetConfigPanel` 的 `_bind_*` 方法读写配置字典，确保与预览和保存逻辑兼容。

