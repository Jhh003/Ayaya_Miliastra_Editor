"""
组件配置 - 自定义变量
基于知识库文档定义的自定义变量组件配置项
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any
from enum import Enum

from engine.type_registry import (
    TYPE_BOOLEAN,
    TYPE_BOOLEAN_LIST,
    TYPE_CAMP,
    TYPE_CAMP_LIST,
    TYPE_COMPONENT_ID,
    TYPE_COMPONENT_ID_LIST,
    TYPE_CONFIG_ID,
    TYPE_CONFIG_ID_LIST,
    TYPE_DICT,
    TYPE_ENTITY,
    TYPE_ENTITY_LIST,
    TYPE_FLOAT,
    TYPE_FLOAT_LIST,
    TYPE_GUID,
    TYPE_GUID_LIST,
    TYPE_INTEGER,
    TYPE_INTEGER_LIST,
    TYPE_STRING,
    TYPE_STRING_LIST,
    TYPE_STRUCT,
    TYPE_STRUCT_LIST,
    TYPE_VECTOR3,
    TYPE_VECTOR3_LIST,
)


class VariableDataType(Enum):
    """自定义变量数据类型（自定义变量.md 第7-21行）"""
    # 基础数据类型
    INTEGER = TYPE_INTEGER
    FLOAT = TYPE_FLOAT
    STRING = TYPE_STRING
    BOOLEAN = TYPE_BOOLEAN
    VECTOR3 = TYPE_VECTOR3
    ENTITY = TYPE_ENTITY
    GUID = TYPE_GUID
    COMPONENT_ID = TYPE_COMPONENT_ID
    CONFIG_ID = TYPE_CONFIG_ID
    CAMP = TYPE_CAMP
    STRUCT = TYPE_STRUCT
    
    # 列表数据类型
    INTEGER_LIST = TYPE_INTEGER_LIST
    FLOAT_LIST = TYPE_FLOAT_LIST
    STRING_LIST = TYPE_STRING_LIST
    BOOLEAN_LIST = TYPE_BOOLEAN_LIST
    VECTOR3_LIST = TYPE_VECTOR3_LIST
    ENTITY_LIST = TYPE_ENTITY_LIST
    GUID_LIST = TYPE_GUID_LIST
    COMPONENT_ID_LIST = TYPE_COMPONENT_ID_LIST
    CONFIG_ID_LIST = TYPE_CONFIG_ID_LIST
    CAMP_LIST = TYPE_CAMP_LIST
    STRUCT_LIST = TYPE_STRUCT_LIST
    
    # 字典数据类型（所有字典数据类型）
    DICT_ALL = "所有字典数据类型"

    def to_canonical_type_name(self) -> str:
        """将枚举值映射为引擎的规范中文类型名。

        说明：
        - `DICT_ALL` 是历史上的“集合类型”表达，用于 UI 选择“字典”这一大类；
          在需要落到具体类型名时，统一映射为 `字典`。
        """
        if self is VariableDataType.DICT_ALL:
            return TYPE_DICT
        return str(self.value)


@dataclass
class CustomVariableConfig:
    """
    自定义变量配置
    """
    # 自定义变量名（唯一序号，不允许重名）
    variable_name: str
    # 自定义变量数据类型（强类型，必须明确）
    data_type: VariableDataType
    # 默认值（实体创建时的初始值）
    default_value: Any = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "变量名": self.variable_name,
            "数据类型": self.data_type.value,
            "默认值": self.default_value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CustomVariableConfig':
        data_type_str = data.get("数据类型", VariableDataType.INTEGER.value)
        data_type = VariableDataType(data_type_str)
        return cls(
            variable_name=data.get("变量名", ""),
            data_type=data_type,
            default_value=data.get("默认值")
        )


@dataclass
class CustomVariableComponentConfig:
    """
    自定义变量组件配置
    """
    # 组件内定义的所有自定义变量
    variables: List[CustomVariableConfig] = field(default_factory=list)
    
    def add_variable(self, variable: CustomVariableConfig) -> bool:
        """添加自定义变量，检查重名"""
        # 检查是否重名（自定义变量.md 第6行）
        for existing_var in self.variables:
            if existing_var.variable_name == variable.variable_name:
                return False
        self.variables.append(variable)
        return True
    
    def remove_variable(self, variable_name: str) -> bool:
        """移除自定义变量"""
        for index, var in enumerate(self.variables):
            if var.variable_name == variable_name:
                self.variables.pop(index)
                return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "已定义自定义变量": [var.to_dict() for var in self.variables]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CustomVariableComponentConfig':
        variables_data = data.get("已定义自定义变量", [])
        variables = [CustomVariableConfig.from_dict(var_data) for var_data in variables_data]
        return cls(variables=variables)

