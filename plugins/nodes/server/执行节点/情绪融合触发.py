from __future__ import annotations
from engine.nodes.node_spec import node_spec
from plugins.nodes.shared.server_执行节点_impl_helpers import *
from engine.utils.logging.logger import log_info


@node_spec(
    name="情绪融合触发",
    category="执行节点",
    inputs=[
        ("流程入", "流程"),
        ("目标实体", "实体"),
        ("情绪类型A", "字符串"),
        ("情绪类型B", "字符串"),
        ("消耗量A", "整数"),
        ("消耗量B", "整数"),
    ],
    outputs=[
        ("流程出", "流程"),
        ("触发成功", "布尔值"),
        ("融合效果", "字符串"),
        ("效果强度", "浮点数"),
    ],
    description="消耗两种不同类型的情绪值触发融合效果，产生更强大的复合效果。",
    doc_reference="服务器节点/执行节点/九权天部.md",
    input_enum_options={
        "情绪类型A": ["愤怒", "恐惧", "绝望"],
        "情绪类型B": ["愤怒", "恐惧", "绝望"],
    },
)
def 情绪融合触发(game, 目标实体, 情绪类型A, 情绪类型B, 消耗量A, 消耗量B):
    """消耗两种不同类型的情绪值触发融合效果

    情绪融合效果：
    - 愤怒+恐惧=震慑：范围伤害+减速
    - 愤怒+绝望=毁灭：范围伤害+降低攻击力
    - 恐惧+绝望=崩溃：持续伤害+攻击力降低
    - 同类型情绪：触发失败

    效果强度与消耗的情绪值总量成正比
    """
    if 情绪类型A == 情绪类型B:
        log_info(f"[情绪融合触发] 融合失败：不能融合相同类型的情绪")
        return False, "无", 0.0

    var_name_a = f"情绪_{情绪类型A}"
    var_name_b = f"情绪_{情绪类型B}"
    current_a = game.get_custom_variable(目标实体, var_name_a, 0)
    current_b = game.get_custom_variable(目标实体, var_name_b, 0)

    if current_a < 消耗量A or current_b < 消耗量B:
        log_info(f"[情绪融合触发] 情绪值不足: {情绪类型A}={current_a}/{消耗量A}, {情绪类型B}={current_b}/{消耗量B}")
        return False, "无", 0.0

    # 消耗情绪值
    game.set_custom_variable(目标实体, var_name_a, current_a - 消耗量A, True)
    game.set_custom_variable(目标实体, var_name_b, current_b - 消耗量B, True)

    # 清除过载状态
    game.set_custom_variable(目标实体, f"情绪过载_{情绪类型A}", False, True)
    game.set_custom_variable(目标实体, f"情绪过载_{情绪类型B}", False, True)

    # 确定融合效果
    emotion_pair = frozenset([情绪类型A, 情绪类型B])
    fusion_effects = {
        frozenset(["愤怒", "恐惧"]): "震慑",
        frozenset(["愤怒", "绝望"]): "毁灭",
        frozenset(["恐惧", "绝望"]): "崩溃",
    }
    fusion_effect = fusion_effects.get(emotion_pair, "未知融合")

    # 计算效果强度（基于消耗量总和）
    total_consumed = 消耗量A + 消耗量B
    effect_strength = 1.0 + (total_consumed - 2) * 0.15

    # 设置融合效果标记
    game.set_custom_variable(目标实体, f"情绪融合_{fusion_effect}", effect_strength, True)

    log_info(f"[情绪融合触发] {情绪类型A}+{情绪类型B}={fusion_effect}，强度{effect_strength:.1f}")
    return True, fusion_effect, effect_strength
