from __future__ import annotations
from engine.nodes.node_spec import node_spec
from plugins.nodes.shared.server_执行节点_impl_helpers import *
from engine.utils.logging.logger import log_info


@node_spec(
    name="物质属性重置",
    category="执行节点",
    inputs=[
        ("流程入", "流程"),
        ("目标实体", "实体"),
        ("属性类型", "字符串"),
    ],
    outputs=[
        ("流程出", "流程"),
        ("重置成功", "布尔值"),
    ],
    description="重置目标实体指定类型的物质属性修改效果。",
    doc_reference="服务器节点/执行节点/九权天部.md",
    input_enum_options={
        "属性类型": ["攻击力", "攻击范围", "攻击速度", "元素伤害", "攻击穿透", "攻击吸血", "全部"],
    },
)
def 物质属性重置(game, 目标实体, 属性类型):
    """重置目标实体指定类型的物质属性修改效果

    可重置的属性类型：
    - 攻击力、攻击范围、攻击速度、元素伤害、攻击穿透、攻击吸血
    - 全部：重置所有物质属性修改效果

    用于在效果过期或主动取消时清除属性修改
    """
    attribute_types = ["攻击力", "攻击范围", "攻击速度", "元素伤害", "攻击穿透", "攻击吸血"]

    if 属性类型 == "全部":
        for attr_type in attribute_types:
            effect_var_name = f"物质属性_{attr_type}"
            end_time_var_name = f"物质属性结束时间_{attr_type}"
            game.set_custom_variable(目标实体, effect_var_name, 0.0, True)
            game.set_custom_variable(目标实体, end_time_var_name, 0.0, True)
        log_info(f"[物质属性重置] 已重置全部物质属性修改效果")
        return True
    else:
        effect_var_name = f"物质属性_{属性类型}"
        end_time_var_name = f"物质属性结束时间_{属性类型}"
        game.set_custom_variable(目标实体, effect_var_name, 0.0, True)
        game.set_custom_variable(目标实体, end_time_var_name, 0.0, True)
        log_info(f"[物质属性重置] 已重置{属性类型}属性修改效果")
        return True
