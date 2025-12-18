"""验证层数据类型规则（兼容转发层）

历史上 `engine.validate.rules.datatype_rules` 与 `engine.configs.rules.datatype_rules`
各自维护过一份数据类型清单，容易造成漂移。

现在类型体系的唯一事实来源为 `engine.type_registry`；
本模块仅保留旧导入路径以兼容历史代码/测试。
"""

from engine.configs.rules.datatype_rules import (  # noqa: F401
    BASE_TYPES,
    LIST_TYPES,
    TYPE_CONVERSIONS,
    can_convert_type,
    get_type_default,
    get_type_info,
)

