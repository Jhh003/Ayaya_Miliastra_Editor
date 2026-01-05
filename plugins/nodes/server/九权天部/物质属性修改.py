from __future__ import annotations
from engine.nodes.node_spec import node_spec
from plugins.nodes.shared.server_执行节点_impl_helpers import *
from engine.utils.logging.logger import log_info


@node_spec(
    name="物质属性修改",
    category="执行节点",
    inputs=[
        ("流程入", "流程"),
        ("目标实体", "实体"),
        ("消耗量", "整数"),
        ("属性类型", "字符串"),
        ("增益百分比", "浮点数"),
        ("持续时间", "浮点数"),
    ],
    outputs=[
        ("流程出", "流程"),
        ("修改成功", "布尔值"),
        ("剩余物质核心", "整数"),
    ],
    description="消耗物质核心修改自身武器属性，效果持续指定时间。",
    doc_reference="服务器节点/执行节点/九权天部.md",
    input_enum_options={
        "属性类型": ["攻击力", "攻击范围", "攻击速度", "元素伤害", "攻击穿透", "攻击吸血"],
    },
)
def 物质属性修改(game, 目标实体, 消耗量, 属性类型, 增益百分比, 持续时间):
    """消耗物质核心修改自身武器属性

    可修改的属性类型：
    - 攻击力：增加武器攻击力
    - 攻击范围：增加武器攻击范围
    - 攻击速度：增加武器攻击速度
    - 元素伤害：武器附带元素伤害
    - 攻击穿透：增加攻击穿透率
    - 攻击吸血：增加攻击吸血效果

    效果有持续时间限制，默认5秒
    """
    current_mc = game.get_custom_variable(目标实体, "物质核心", 0)

    if current_mc < 消耗量:
        log_info(f"[物质属性修改] 物质核心不足: {current_mc}/{消耗量}，修改失败")
        return False, current_mc

    # 消耗物质核心
    new_mc = current_mc - 消耗量
    game.set_custom_variable(目标实体, "物质核心", new_mc, True)

    # 设置属性修改效果
    effect_var_name = f"物质属性_{属性类型}"
    game.set_custom_variable(目标实体, effect_var_name, 增益百分比, True)

    # 设置效果结束时间
    end_time_var_name = f"物质属性结束时间_{属性类型}"
    current_time = time.time()
    game.set_custom_variable(目标实体, end_time_var_name, current_time + 持续时间, True)

    log_info(f"[物质属性修改] 消耗{消耗量}MC，{属性类型}+{增益百分比*100:.0f}%，持续{持续时间}秒，剩余{new_mc}MC")
    return True, new_mc
