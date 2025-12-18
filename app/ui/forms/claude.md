## 目录用途
`ui/forms/` 集中存放 UI 层“表单与对话框”相关的轻量辅助模块，用于在已统一的对话框外壳（`BaseDialog` / `FormDialog` / `ManagementDialogBase`）之上，以声明式或少量命令式代码快速拼装表单内容。

## 当前状态
- `schema_dialog.py`：封装 `FormDialogBuilder` 等表单构建辅助类，负责在 `FormDialog` 外壳上按行追加常见输入控件（单行文本、多行文本、下拉框、整数/浮点数输入、复选框、颜色选择、向量3编辑器等），并暴露 `dialog` 与底层 `form_layout` 以便在调用方按需添加自定义分组或说明文字。
  - 内部控件已统一套用主题输入/下拉/数值框样式与按钮样式，颜色选择行沿用 ThemeManager 的输入/按钮样式。
- `schema_bound_form.py`：可嵌入面板的“schema 表单”绑定器 `SchemaBoundForm`，用 `FormFieldSpec` 列表声明字段并绑定到 dict 模型，负责控件创建、主题样式套用以及“模型 <-> 控件”双向同步（不承载业务校验逻辑）。
- 该目录仅提供 UI 级 helper，不承载任何业务逻辑与资源访问；表单结果的解释与持久化仍由上层页面、Section 或控制器负责。

## 注意事项
- 新增表单类对话框时，应优先基于 `app.ui.foundation.base_widgets.FormDialog` 或 `BaseDialog` / `ManagementDialogBase` 作为外壳，再通过本目录的 helper 组装字段，避免在业务模块中直接从 `QDialog` 派生和手写按钮区。
- 复杂业务表单（例如需要内联表格或多标签页的管理配置）应将“数据结构与校验逻辑”放在 Section 或面板模块中，本目录的辅助类仅负责控件创建与布局，不参与业务规则判断。
- 不在本目录中使用 `try/except` 吞掉异常，出错应直接抛出或由上层统一处理。


