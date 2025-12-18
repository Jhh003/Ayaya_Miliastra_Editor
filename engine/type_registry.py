from __future__ import annotations

"""
Type Registry（唯一事实来源）
===========================

本文件集中维护“规范中文类型名”及其语义规则，作为以下模块的唯一类型来源：
- 图变量（GRAPH_VARIABLES / GraphVariableConfig）
- 结构体字段类型（基础结构体 / 局内存档结构体）
- 端口类型（流程/泛型/列表/字典及别名字典）
- 类型名校验（TypeNameRule）、复合节点引脚类型策略等

约束：
- 纯 Python / 纯数据与纯函数，不依赖 UI，不做 I/O，不吞异常。
- 其它模块不得再维护平行的类型清单；应从本文件导入或通过兼容转发模块导入。
"""

from types import MappingProxyType
from typing import Any, Dict, Final, Mapping, MutableMapping, Set, Tuple

# ============================================================================
# 规范中文类型名（基础/容器/结构体）
# ============================================================================

TYPE_SUFFIX_LIST: Final[str] = "列表"

TYPE_ENTITY: Final[str] = "实体"
TYPE_GUID: Final[str] = "GUID"
TYPE_INTEGER: Final[str] = "整数"
TYPE_BOOLEAN: Final[str] = "布尔值"
TYPE_FLOAT: Final[str] = "浮点数"
TYPE_STRING: Final[str] = "字符串"
TYPE_VECTOR3: Final[str] = "三维向量"
TYPE_COMPONENT_ID: Final[str] = "元件ID"
TYPE_CONFIG_ID: Final[str] = "配置ID"
TYPE_CAMP: Final[str] = "阵营"

TYPE_DICT: Final[str] = "字典"
TYPE_STRUCT: Final[str] = "结构体"

TYPE_ENTITY_LIST: Final[str] = f"{TYPE_ENTITY}{TYPE_SUFFIX_LIST}"
TYPE_GUID_LIST: Final[str] = f"{TYPE_GUID}{TYPE_SUFFIX_LIST}"
TYPE_INTEGER_LIST: Final[str] = f"{TYPE_INTEGER}{TYPE_SUFFIX_LIST}"
TYPE_BOOLEAN_LIST: Final[str] = f"{TYPE_BOOLEAN}{TYPE_SUFFIX_LIST}"
TYPE_FLOAT_LIST: Final[str] = f"{TYPE_FLOAT}{TYPE_SUFFIX_LIST}"
TYPE_STRING_LIST: Final[str] = f"{TYPE_STRING}{TYPE_SUFFIX_LIST}"
TYPE_VECTOR3_LIST: Final[str] = f"{TYPE_VECTOR3}{TYPE_SUFFIX_LIST}"
TYPE_COMPONENT_ID_LIST: Final[str] = f"{TYPE_COMPONENT_ID}{TYPE_SUFFIX_LIST}"
TYPE_CONFIG_ID_LIST: Final[str] = f"{TYPE_CONFIG_ID}{TYPE_SUFFIX_LIST}"
TYPE_CAMP_LIST: Final[str] = f"{TYPE_CAMP}{TYPE_SUFFIX_LIST}"
TYPE_STRUCT_LIST: Final[str] = f"{TYPE_STRUCT}{TYPE_SUFFIX_LIST}"

# ============================================================================
# 端口/标注相关特殊类型
# ============================================================================

TYPE_FLOW: Final[str] = "流程"
TYPE_GENERIC: Final[str] = "泛型"
TYPE_GENERIC_LIST: Final[str] = "泛型列表"
TYPE_GENERIC_DICT: Final[str] = "泛型字典"
TYPE_ENUM: Final[str] = "枚举"

# 历史/兼容：用于“Python 内置类型 list → 中文端口类型”映射的占位类型
TYPE_LIST_PLACEHOLDER: Final[str] = "列表"

# 严禁的旧别名（从源头掐灭，避免出现多套“泛型”术语）
BANNED_TYPE_ALIASES: Final[Set[str]] = {"通用", "Any", "any", "ANY"}

# Python 内置类型名（用于复合节点 pin_type 成品校验等场景）
PYTHON_BUILTIN_TYPE_NAMES: Final[Set[str]] = {"int", "float", "str", "bool", "list", "dict"}


# ============================================================================
# 数据类型规则：基础类型 / 列表类型 / 类型转换（供节点与规则复用）
# ============================================================================

_BASE_TYPES_MUT: MutableMapping[str, Dict[str, Any]] = {
    TYPE_ENTITY: {
        "display_name": TYPE_ENTITY,
        "description": "代表了一个运行时的实体",
        "default": 0,
        "default_meaning": "无实际意义，指向了一个不存在的实体",
        "reference": "基础概念.md:145",
    },
    TYPE_GUID: {
        "display_name": TYPE_GUID,
        "description": "实体在场景中布设时的GUID。对于动态创建的实体来说GUID=0",
        "default": 0,
        "reference": "基础概念.md:146",
        "note": "GUID 在引擎内就是数字 ID（也可用字符串包裹数字）表示的标识，纯数字形态是正常的；若编辑器把数字 GUID 当格式错误标红，可在使用处忽略对应的静态检查提示。",
    },
    TYPE_INTEGER: {
        "display_name": TYPE_INTEGER,
        "description": "32位带符号整型数",
        "default": 0,
        "range": (-2147483648, 2147483647),
        "overflow": "超出范围会自动上/下溢出",
        "overflow_example": "2147483648会自动变为-2147483648",
        "reference": "基础概念.md:147",
    },
    TYPE_BOOLEAN: {
        "display_name": TYPE_BOOLEAN,
        "description": "布尔型。只有【是】和【否】两个取值",
        "default": False,
        "values": [True, False],
        "reference": "基础概念.md:148",
    },
    TYPE_FLOAT: {
        "display_name": TYPE_FLOAT,
        "description": "单精度浮点数",
        "default": 0.0,
        "range": "约±1.5 x 10^−45 至 ±3.4 x 10^38",
        "overflow": "修正为0",
        "overflow_note": "与多数编程语言不同，不使用Inf或NaN，发生溢出时修正为0",
        "reference": "基础概念.md:149",
    },
    TYPE_STRING: {
        "display_name": TYPE_STRING,
        "description": "字符串类型，用于表示文本数据",
        "default": "",
        "max_length_en": 40,  # 英文字符
        "max_length_zh": 13,  # 约13个中文字符
        "note": "最长不能超过40个英文字符（约13个中文字符）",
        "reference": "基础概念.md:150",
    },
    TYPE_VECTOR3: {
        "display_name": TYPE_VECTOR3,
        "description": "三维向量类型，每个分量都是一个浮点数",
        "default": (0, 0, 0),
        "component_overflow": "单个分量发生溢出时，按照浮点数的溢出规则处理",
        "reference": "基础概念.md:151",
    },
    TYPE_COMPONENT_ID: {
        "display_name": TYPE_COMPONENT_ID,
        "description": "元件的ID，对应一个特定的元件",
        "default": 0,
        "default_meaning": "无实际意义，指向了一个不存在的元件",
        "reference": "基础概念.md:152",
    },
    TYPE_CONFIG_ID: {
        "display_name": TYPE_CONFIG_ID,
        "description": "通用配置的ID，例如：单位状态的ID、职业的ID等",
        "default": 0,
        "default_meaning": "无实际意义，指向了一个不存在的配置",
        "reference": "基础概念.md:153",
    },
    TYPE_CAMP: {
        "display_name": TYPE_CAMP,
        "description": "阵营类型，通常用于表示单位/实体所属阵营",
        "default": 0,
        "reference": "基础概念.md:191",
    },
}

_LIST_TYPES_MUT: MutableMapping[str, Dict[str, Any]] = {
    TYPE_ENTITY_LIST: {
        "base_type": TYPE_ENTITY,
        "description": "实体列表类型",
        "index_start": 0,  # 基础概念.md:173 "列表的索引从0开始计数"
        "pass_by": "引用",  # 基础概念.md:174 "列表使用【引用传值】的形式进行参数传递"
        "reference": "基础概念.md:160",
    },
    TYPE_GUID_LIST: {
        "base_type": TYPE_GUID,
        "index_start": 0,
        "pass_by": "引用",
        "reference": "基础概念.md:161",
    },
    TYPE_INTEGER_LIST: {
        "base_type": TYPE_INTEGER,
        "index_start": 0,
        "pass_by": "引用",
        "example": "{1, 3, 5, 7, 9}",  # 基础概念.md:170
        "reference": "基础概念.md:162",
    },
    TYPE_BOOLEAN_LIST: {
        "base_type": TYPE_BOOLEAN,
        "index_start": 0,
        "pass_by": "引用",
        "reference": "基础概念.md:163",
    },
    TYPE_FLOAT_LIST: {
        "base_type": TYPE_FLOAT,
        "index_start": 0,
        "pass_by": "引用",
        "reference": "基础概念.md:164",
    },
    TYPE_STRING_LIST: {
        "base_type": TYPE_STRING,
        "index_start": 0,
        "pass_by": "引用",
        "reference": "基础概念.md:165",
    },
    TYPE_VECTOR3_LIST: {
        "base_type": TYPE_VECTOR3,
        "index_start": 0,
        "pass_by": "引用",
        "reference": "基础概念.md:166",
    },
    TYPE_COMPONENT_ID_LIST: {
        "base_type": TYPE_COMPONENT_ID,
        "index_start": 0,
        "pass_by": "引用",
        "reference": "基础概念.md:167",
    },
    TYPE_CONFIG_ID_LIST: {
        "base_type": TYPE_CONFIG_ID,
        "index_start": 0,
        "pass_by": "引用",
        "reference": "基础概念.md:168",
    },
    TYPE_CAMP_LIST: {
        "base_type": TYPE_CAMP,
        "index_start": 0,
        "pass_by": "引用",
        "reference": "基础概念.md:169",
    },
}

_TYPE_CONVERSIONS_MUT: MutableMapping[Tuple[str, str], Dict[str, Any]] = {
    (TYPE_INTEGER, TYPE_BOOLEAN): {
        "rule": "0转为否，非0转为是",
        "examples": [("0", "否"), ("5", "是")],
        "reference": "基础概念.md:181",
    },
    (TYPE_INTEGER, TYPE_FLOAT): {
        "rule": "整数转浮点数",
        "examples": [("1", "1.0"), ("-2", "-2.0"), ("0", "0.0")],
        "reference": "基础概念.md:182",
    },
    (TYPE_INTEGER, TYPE_STRING): {
        "rule": "整数转字符串",
        "examples": [("1", '"1"'), ("15", '"15"')],
        "reference": "基础概念.md:183",
    },
    (TYPE_BOOLEAN, TYPE_INTEGER): {
        "rule": "否转为0，是转为1",
        "examples": [("否", "0"), ("是", "1")],
        "reference": "基础概念.md:186",
    },
    (TYPE_BOOLEAN, TYPE_STRING): {
        "rule": '返回"是"和"否"',
        "examples": [("否", '"否"'), ("是", '"是"')],
        "reference": "基础概念.md:187",
    },
    (TYPE_FLOAT, TYPE_INTEGER): {
        "rule": "截尾转为整数，与取整节点的截尾功能相同",
        "examples": [("2.5", "2"), ("-1.31", "-1"), ("0.0", "0")],
        "reference": "基础概念.md:188",
    },
    (TYPE_FLOAT, TYPE_STRING): {
        "rule": "输出浮点数对应的字符串，至多保留6位有效数字",
        "examples": [("2.5", '"2.5"'), ("-1.317524", '"-1.31752"')],
        "reference": "基础概念.md:189",
    },
    (TYPE_VECTOR3, TYPE_STRING): {
        "rule": '返回"(分量1,分量2,分量3)"格式的字符串。每个分量保留1位小数',
        "examples": [("(1.05, 2.3, 3)", '"(1.0, 2.3, 3.0)"')],
        "reference": "基础概念.md:190",
    },
    (TYPE_ENTITY, TYPE_STRING): {
        "rule": "输出实体的运行时id",
        "examples": [("某个实体", '"1001"')],
        "reference": "基础概念.md:184",
    },
    (TYPE_GUID, TYPE_STRING): {
        "rule": "输出GUID对应的字符串",
        "examples": [("某个实体", '"100001"')],
        "reference": "基础概念.md:185",
    },
    (TYPE_CAMP, TYPE_STRING): {
        "rule": "返回阵营的id转为的字符串",
        "examples": [("某个实体上的阵营", '"2"')],
        "reference": "基础概念.md:191",
    },
}

# 对外只读视图（避免多处模块在运行期改写常量）
BASE_TYPES: Final[Mapping[str, Mapping[str, Any]]] = MappingProxyType(_BASE_TYPES_MUT)
LIST_TYPES: Final[Mapping[str, Mapping[str, Any]]] = MappingProxyType(_LIST_TYPES_MUT)
TYPE_CONVERSIONS: Final[Mapping[Tuple[str, str], Mapping[str, Any]]] = MappingProxyType(
    _TYPE_CONVERSIONS_MUT
)


# ============================================================================
# 场景允许集合（变量 / 结构体字段 / 复合节点对外引脚 / 端口标注）
# ============================================================================

# 变量类型定义（实体/模板自定义变量 & 节点图变量编辑器 UI 统一使用）
VARIABLE_TYPES: Final[Tuple[str, ...]] = (
    TYPE_STRING,
    TYPE_STRING_LIST,
    TYPE_INTEGER,
    TYPE_INTEGER_LIST,
    TYPE_FLOAT,
    TYPE_FLOAT_LIST,
    TYPE_BOOLEAN,
    TYPE_BOOLEAN_LIST,
    TYPE_VECTOR3,
    TYPE_VECTOR3_LIST,
    TYPE_ENTITY,
    TYPE_ENTITY_LIST,
    TYPE_GUID,
    TYPE_GUID_LIST,
    TYPE_CONFIG_ID,
    TYPE_CONFIG_ID_LIST,
    TYPE_COMPONENT_ID,
    TYPE_COMPONENT_ID_LIST,
    TYPE_CAMP,
    TYPE_CAMP_LIST,
    TYPE_STRUCT,
    TYPE_STRUCT_LIST,
    TYPE_DICT,
)

# 结构体字段支持类型（基础结构体：允许字典；局内存档结构体：不允许字典）
BASIC_STRUCT_SUPPORTED_TYPES: Final[Tuple[str, ...]] = (
    TYPE_ENTITY,
    TYPE_GUID,
    TYPE_INTEGER,
    TYPE_BOOLEAN,
    TYPE_FLOAT,
    TYPE_STRING,
    TYPE_CAMP,
    TYPE_VECTOR3,
    TYPE_COMPONENT_ID,
    TYPE_CONFIG_ID,
    TYPE_STRUCT,
    TYPE_DICT,
    TYPE_ENTITY_LIST,
    TYPE_GUID_LIST,
    TYPE_INTEGER_LIST,
    TYPE_BOOLEAN_LIST,
    TYPE_FLOAT_LIST,
    TYPE_STRING_LIST,
    TYPE_CAMP_LIST,
    TYPE_VECTOR3_LIST,
    TYPE_COMPONENT_ID_LIST,
    TYPE_CONFIG_ID_LIST,
    TYPE_STRUCT_LIST,
)
INGAME_SAVE_STRUCT_SUPPORTED_TYPES: Final[Tuple[str, ...]] = tuple(
    type_name for type_name in BASIC_STRUCT_SUPPORTED_TYPES if type_name != TYPE_DICT
)

# 复合节点对外数据引脚允许：基础/列表/字典（流程单独处理）
COMPOSITE_ALLOWED_DATA_PIN_TYPES: Final[Set[str]] = (
    set(BASE_TYPES.keys()) | set(LIST_TYPES.keys()) | {TYPE_DICT}
)

# 端口类型标注允许集合（用于解析/保存 pin_type / 虚拟引脚等）
PIN_TYPE_ANNOTATION_ALLOWED_TYPES: Final[Set[str]] = (
    set(BASE_TYPES.keys())
    | set(LIST_TYPES.keys())
    | {TYPE_GENERIC, TYPE_DICT, TYPE_LIST_PLACEHOLDER, TYPE_GENERIC_LIST, TYPE_GENERIC_DICT, TYPE_FLOW}
)

# 基础类型 -> 列表类型映射（供类型推断与自动化复用）
BASE_TO_LIST_TYPE_MAP: Final[Mapping[str, str]] = MappingProxyType(
    {
        TYPE_ENTITY: TYPE_ENTITY_LIST,
        TYPE_GUID: TYPE_GUID_LIST,
        TYPE_INTEGER: TYPE_INTEGER_LIST,
        TYPE_BOOLEAN: TYPE_BOOLEAN_LIST,
        TYPE_FLOAT: TYPE_FLOAT_LIST,
        TYPE_STRING: TYPE_STRING_LIST,
        TYPE_VECTOR3: TYPE_VECTOR3_LIST,
        TYPE_COMPONENT_ID: TYPE_COMPONENT_ID_LIST,
        TYPE_CONFIG_ID: TYPE_CONFIG_ID_LIST,
        TYPE_CAMP: TYPE_CAMP_LIST,
        TYPE_STRUCT: TYPE_STRUCT_LIST,
    }
)


# ============================================================================
# 工具函数（避免各处复制粘贴：别名字典解析、类型默认值/信息查询等）
# ============================================================================


def normalize_type_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def is_list_type_name(type_name: object) -> bool:
    text = normalize_type_text(type_name)
    if text == "":
        return False
    return text.endswith(TYPE_SUFFIX_LIST)


def is_dict_type_name(type_name: object) -> bool:
    text = normalize_type_text(type_name)
    if text == "":
        return False
    if text == TYPE_DICT:
        return True
    return text.endswith(TYPE_DICT)


def parse_typed_dict_alias(type_name: object) -> tuple[bool, str, str]:
    """解析类似“字符串-GUID列表字典”或“字符串_GUID列表字典”的别名字典类型。

    约定格式：
    - 统一以“字典”结尾，例如：`字符串_GUID列表字典` 或 `字符串-GUID列表字典`
    - 以第一个“-”或“_”划分键/值类型名：左侧为键类型，右侧为值类型
    - 键/值类型名本身必须是已有的合法类型名（合法性由调用方结合允许集合判定）
    """
    if not isinstance(type_name, str):
        return False, "", ""

    text = type_name.strip()
    if not text or not text.endswith(TYPE_DICT):
        return False, "", ""

    body = text[: -len(TYPE_DICT)].strip()
    if not body:
        return False, "", ""

    dash_index = body.find("-")
    underscore_index = body.find("_")

    separator_index = -1
    if dash_index >= 0 and underscore_index >= 0:
        separator_index = min(dash_index, underscore_index)
    elif dash_index >= 0:
        separator_index = dash_index
    else:
        separator_index = underscore_index

    if separator_index <= 0 or separator_index >= len(body) - 1:
        return False, "", ""

    key_raw = body[:separator_index]
    value_raw = body[separator_index + 1 :]
    key_type = key_raw.strip()
    value_type = value_raw.strip()
    if not key_type or not value_type:
        return False, "", ""

    return True, key_type, value_type


def get_type_default(type_name: str):
    """获取类型的默认值（基础类型取其定义默认值；列表类型默认空列表；其它返回 None）。"""
    if type_name in BASE_TYPES:
        return BASE_TYPES[type_name]["default"]
    if type_name in LIST_TYPES:
        return []
    return None


def can_convert_type(from_type: str, to_type: str) -> tuple[bool, str]:
    """检查是否可以进行类型转换

    Returns:
        (是否可以转换, 转换规则说明)
    """
    key = (from_type, to_type)
    if key in TYPE_CONVERSIONS:
        conversion = TYPE_CONVERSIONS[key]
        return True, str(conversion.get("rule", ""))
    return False, f"不支持从'{from_type}'到'{to_type}'的类型转换"


def get_type_info(type_name: str) -> dict:
    """获取类型的完整信息（基础/列表；未找到返回空 dict）。"""
    if type_name in BASE_TYPES:
        return dict(BASE_TYPES[type_name])
    if type_name in LIST_TYPES:
        return dict(LIST_TYPES[type_name])
    return {}


