# 贡献指南（展示型仓库）

本仓库是“Graph Code → 节点图/复合节点”的离线工具链与 UI 查看器。欢迎提交 bug 修复、回归测试与工具链改进。

## 你可以贡献什么
- 修复引擎/工具链/验证器的 bug
- 为重要规则补充最小可复现测试（优先）
- 改进文档（仅限仓库内公开文档：README、各公开目录的 `claude.md`）

## 你不应该提交什么
- 任何私密资源、账号信息、Token、截图、个人工程存档
- `docs/` 与 `projects/` 目录内容（展示型发布策略：不随仓库分发）
- 运行期缓存与本地状态（见根目录 `.gitignore`）

## 开发环境
- Windows 10/11
- Python 3.10+
- 依赖安装（PowerShell，逐行执行）：

```powershell
pip install -r requirements-dev.txt -c constraints.txt
```

## 运行测试

```powershell
python -X utf8 -m pytest
```

## 节点图/复合节点的校验（提交前建议）
如果你新增/修改了节点图或复合节点源码，请在提交前运行校验并根据输出修正：

```powershell
python -X utf8 -m tools.validate.validate_graphs --all
```

> 注意：不要直接运行 `run_app.py` / `main_package.py` 这类入口；工具脚本与校验脚本请使用 `python -m ...` 的模块方式运行。

## 目录约定（重要）
- 每个公开目录都有一个 `claude.md`，用于描述“目录用途 / 当前状态 / 注意事项”（不写修改历史）。
- 资源库采用“默认忽略 + 白名单放行示例”的策略：不要扩大白名单范围，除非明确确认资源可公开且不会泄露隐私。


