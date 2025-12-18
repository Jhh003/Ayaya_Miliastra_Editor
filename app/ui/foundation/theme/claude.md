## 目录用途
`ui/foundation/theme/` 承载主题系统的核心登记处，集中管理配色、尺寸、图标、渐变等 token 以及各类样式工厂、语义模板与 HTML 片段。该目录负责提供统一的主题 API，供 `ThemeManager` 按需组装与缓存。

## 当前状态
- `theme_registry.py` 暴露 `Colors/Sizes/Icons/Gradients` 等 token，并为样式模块提供单一入口。
- `tokens/` 存放所有基础常量，保持纯数据、无 Qt 依赖；其中 `colors.py` 通过类方法在浅色/深色调色板之间切换，供 `ThemeManager` 在启动阶段按需选择。
- `styles/` 划分组件样式、组合样式与 HTML 模板，输出纯字符串工厂，避免 `ThemeManager` 继续承载长 QSS。
- `combo_proxy_style.py` 提供下拉箭头代理样式，使用 `State_Enabled` 推断禁用态颜色，兼容 PyQt6 状态枚举。
- 目录提供 `__init__.py` 以便上层通过 `app.ui.foundation.theme` 导入所需对象。
- `theme_manager.py` 在应用启动时统一注入调色板、全局样式，安装扁平箭头的 `ComboArrowProxyStyle`（替换默认下拉箭头绘制）以及滚轮误触过滤器。

## 注意事项
- Token 仅包含常量或简单函数，不引入运行时副作用；若需计算型值，请在 styles 层处理。
- 样式模块生成的 QSS 字符串不得调用 Qt API，确保可在任意线程构建。
- 新增 token 或样式时同步更新本目录说明，使“用途/状态/注意事项”与实际结构保持一致。


