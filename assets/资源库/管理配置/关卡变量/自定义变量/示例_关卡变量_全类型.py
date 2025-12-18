from __future__ import annotations

from engine.graph.models.package_model import LevelVariableDefinition


VARIABLE_FILE_ID = "sample_custom_variables_all_types"
VARIABLE_FILE_NAME = "示例_关卡变量_全类型"


LEVEL_VARIABLES: list[LevelVariableDefinition] = [
    LevelVariableDefinition(
        variable_id="var_sample_integer_counter",
        variable_name="示例_计数器_整数",
        variable_type="整数",
        default_value=0,
        is_global=True,
        description="示例：全局整数变量",
        metadata={"category": "教学示例"},
    ),
    LevelVariableDefinition(
        variable_id="var_sample_float_ratio",
        variable_name="示例_倍率_浮点数",
        variable_type="浮点数",
        default_value=1.25,
        is_global=True,
        description="示例：全局浮点数变量",
        metadata={"category": "教学示例"},
    ),
    LevelVariableDefinition(
        variable_id="var_sample_boolean_switch",
        variable_name="示例_开关_布尔值",
        variable_type="布尔值",
        default_value=False,
        is_global=True,
        description="示例：全局布尔开关",
        metadata={"category": "教学示例"},
    ),
    LevelVariableDefinition(
        variable_id="var_sample_string_note",
        variable_name="示例_备注_字符串",
        variable_type="字符串",
        default_value="示例默认文本",
        is_global=True,
        description="示例：全局字符串变量",
        metadata={"category": "教学示例"},
    ),
    LevelVariableDefinition(
        variable_id="var_sample_vector3_spawn",
        variable_name="示例_出生点_三维向量",
        variable_type="三维向量",
        default_value=(0.0, 0.0, 0.0),
        is_global=True,
        description="示例：三维向量（位置/方向）变量",
        metadata={"category": "教学示例"},
    ),
    LevelVariableDefinition(
        variable_id="var_sample_guid",
        variable_name="示例_GUID",
        variable_type="GUID",
        default_value="00000000-0000-0000-0000-000000000000",
        is_global=True,
        description="示例：GUID 字符串",
        metadata={"category": "教学示例"},
    ),
    LevelVariableDefinition(
        variable_id="var_sample_integer_list",
        variable_name="示例_整数列表",
        variable_type="整数列表",
        default_value=[1, 2, 3],
        is_global=True,
        description="示例：整数列表",
        metadata={"category": "教学示例"},
    ),
    LevelVariableDefinition(
        variable_id="var_sample_string_list",
        variable_name="示例_字符串列表",
        variable_type="字符串列表",
        default_value=["条目A", "条目B", "条目C"],
        is_global=True,
        description="示例：字符串列表",
        metadata={"category": "教学示例"},
    ),
    LevelVariableDefinition(
        variable_id="var_sample_boolean_list",
        variable_name="示例_布尔值列表",
        variable_type="布尔值列表",
        default_value=[True, False, True],
        is_global=True,
        description="示例：布尔值列表",
        metadata={"category": "教学示例"},
    ),
    LevelVariableDefinition(
        variable_id="var_sample_vector3_list",
        variable_name="示例_三维向量列表",
        variable_type="三维向量列表",
        default_value=[(0.0, 0.0, 0.0), (1.0, 2.0, 3.0)],
        is_global=True,
        description="示例：三维向量列表",
        metadata={"category": "教学示例"},
    ),
    LevelVariableDefinition(
        variable_id="var_sample_flat_dict",
        variable_name="示例_界面展示_字典(一层)",
        variable_type="字典",
        default_value={
            "当前钻石": 0,
            "当前金币": 0,
            "当前提示": "示例提示文本",
            "是否开启": False,
            "当前计数": 0,
        },
        is_global=True,
        description="示例：字典类型（仅允许一层键值表，不在 value 中再嵌套字典）",
        metadata={"category": "教学示例"},
    ),
    LevelVariableDefinition(
        variable_id="var_sample_struct_list",
        variable_name="示例_结构体列表(基础结构体)",
        variable_type="结构体列表",
        default_value={
            "struct_id": "struct_all_supported_types_example",
            "items": [
                {
                    "name": "条目1",
                    "fields": {
                        "整数字段": "1",
                        "布尔值字段": "True",
                        "浮点数字段": "1.5",
                        "字符串字段": "示例字符串",
                        "GUID字段": "00000000-0000-0000-0000-000000000001",
                        "三维向量字段": "0,0,0",
                    },
                }
            ],
        },
        is_global=True,
        description="示例：结构体列表（引用基础结构体 struct_all_supported_types_example；字段值统一使用字符串）",
        metadata={"category": "教学示例"},
    ),
]


