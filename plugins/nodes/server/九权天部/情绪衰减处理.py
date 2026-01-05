from __future__ import annotations
from engine.nodes.node_spec import node_spec
from plugins.nodes.shared.server_执行节点_impl_helpers import *
from engine.utils.logging.logger import log_info


@node_spec(
    name="情绪衰减处理",
    category="执行节点",
    inputs=[
        ("流程入", "流程"),
        ("目标实体", "实体"),
        ("衰减量", "整数"),
        ("衰减间隔", "浮点数"),
    ],
    outputs=[
        ("流程出", "流程"),
        ("愤怒剩余", "整数"),
        ("恐惧剩余", "整数"),
        ("绝望剩余", "整数"),
    ],
    description="处理目标实体的情绪值衰减。所有类型的情绪值都会随时间缓慢衰减，鼓励主动消耗。",
    doc_reference="服务器节点/执行节点/九权天部.md"
)
def 情绪衰减处理(game, 目标实体, 衰减量, 衰减间隔):
    """处理目标实体的情绪值衰减

    平衡机制：
    - 情绪值随时间缓慢衰减，鼓励主动消耗
    - 衰减量：每次衰减减少的情绪值，默认1点
    - 衰减间隔：衰减触发的时间间隔（秒），默认5.0秒

    此节点应配合定时器节点使用
    """
    emotion_types = ["愤怒", "恐惧", "绝望"]
    results = []

    for emotion_type in emotion_types:
        var_name = f"情绪_{emotion_type}"
        current_value = game.get_custom_variable(目标实体, var_name, 0)

        if current_value > 0:
            new_value = max(0, current_value - 衰减量)
            game.set_custom_variable(目标实体, var_name, new_value, True)

            # 如果衰减到0以下，清除过载状态
            if new_value == 0:
                overload_var_name = f"情绪过载_{emotion_type}"
                game.set_custom_variable(目标实体, overload_var_name, False, True)

            results.append(new_value)
            log_info(f"[情绪衰减处理] {emotion_type}: {current_value} -> {new_value}")
        else:
            results.append(0)

    return results[0], results[1], results[2]
