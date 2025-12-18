# 目录用途
应用层装配：UI/CLI/运行态的组织与对接，仅通过公共 API 使用引擎与插件。

# 公共 API
不对外提供库级 API；对外仅有应用入口（CLI/GUI）。

# 依赖边界
- 允许依赖：`engine/*`、`plugins/*`
- 禁止依赖：`assets/*`（除只读）、`tools/*`（除开发期）

# 注意事项
- 运行态状态与缓存集中在 `app/runtime/` 管理。 

# 当前状态
- 设置与配置统一从 `engine.configs.settings` 获取
- 自动化能力仅从 `app.automation` 访问
- 不再依赖任何 `core.*` 兼容层
- `python -X utf8 -m app` 可作为 UI 启动短入口（委托到 `app.cli.run_app`）

