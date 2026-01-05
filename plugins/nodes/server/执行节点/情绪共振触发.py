from __future__ import annotations
from engine.nodes.node_spec import node_spec
from plugins.nodes.shared.server_执行节点_impl_helpers import *
from engine.utils.logging.logger import log_info


@node_spec(
    name="情绪共振触发",
    category="执行节点",
    inputs=[
        ("流程入", "流程"),
        ("目标实体", "实体"),
        ("情绪类型", "字符串"),
        ("消耗量", "整数"),
    ],
    outputs=[
        ("流程出", "流程"),
        ("触发成功", "布尔值"),
        ("剩余情绪值", "整数"),
        ("效果强度", "浮点数"),
    ],
    description="消耗指定数量的情绪值触发情绪共振效果。不同情绪类型产生不同效果。",
    doc_reference="服务器节点/执行节点/九权天部.md",
    input_enum_options={
        "情绪类型": ["愤怒", "恐惧", "绝望", "喜悦", "悲伤"],
    },
)
def 情绪共振触发(game, 目标实体, 情绪类型, 消耗量):
    """消耗情绪值触发情绪共振效果

    情绪共振效果：
    - 愤怒共振：对周围敌人造成范围伤害
    - 恐惧共振：对周围敌人施加群体减速
    - 绝望共振：降低周围敌人的攻击力
    - 喜悦共振：为自身施加增益效果
    - 悲伤共振：对敌人造成持续伤害

    效果强度与消耗的情绪值成正比
    """
    var_name = f"情绪_{情绪类型}"
    current_value = game.get_custom_variable(目标实体, var_name, 0)

    if current_value < 消耗量:
        log_info(f"[情绪共振触发] {情绪类型}情绪值不足: {current_value}/{消耗量}，触发失败")
        return False, current_value, 0.0

    # 消耗情绪值
    new_value = current_value - 消耗量
    game.set_custom_variable(目标实体, var_name, new_value, True)

    # 清除过载状态
    overload_var_name = f"情绪过载_{情绪类型}"
    game.set_custom_variable(目标实体, overload_var_name, False, True)

    # 计算效果强度（基于消耗量）
    # 基础强度1.0，每点情绪值增加0.2强度
    effect_strength = 1.0 + (消耗量 - 1) * 0.2

    # 设置共振效果标记
    resonance_var_name = f"情绪共振_{情绪类型}"
    game.set_custom_variable(目标实体, resonance_var_name, effect_strength, True)

    log_info(f"[情绪共振触发] {情绪类型}共振成功！消耗{消耗量}，剩余{new_value}，强度{effect_strength:.1f}")
    return True, new_value, effect_strength
