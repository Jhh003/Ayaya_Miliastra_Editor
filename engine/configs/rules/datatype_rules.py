"""数据类型规则定义（兼容转发层）

权威类型体系已迁移至 `engine.type_registry`，以保证“单一事实来源”：
- 基础类型/列表类型清单
- 类型转换规则
- 结构体/变量类型允许集合
- 别名字典解析等通用工具

本模块保留原有导入路径与对外 API（`BASE_TYPES` / `LIST_TYPES` / `TYPE_CONVERSIONS` 与工具函数）。
"""

from engine.type_registry import (
    BASE_TYPES,
    LIST_TYPES,
    TYPE_CONVERSIONS,
    can_convert_type,
    get_type_default,
    get_type_info,
)

