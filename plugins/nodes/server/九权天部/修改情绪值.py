from __future__ import annotations
from engine.nodes.node_spec import node_spec
from plugins.nodes.shared.server_执行节点_impl_helpers import *
from engine.utils.logging.logger import log_info


@node_spec(
    name="修改情绪值",
    category="执行节点",
    inputs=[
        ("流程入", "流程"),
        ("目标实体", "实体"),
        ("情绪类型", "字符串"),
        ("变化量", "整数"),
    ],
    outputs=[
        ("流程出", "流程"),
        ("修改后情绪值", "整数"),
        ("是否触发过载", "布尔值"),
    ],
    description="修改目标实体的指定类型情绪值。当情绪达到上限时触发过载状态。",
    doc_reference="服务器节点/执行节点/九权天部.md",
    input_enum_options={
        "情绪类型": ["愤怒", "恐惧", "绝望", "喜悦", "悲伤"],
    },
)
def 修改情绪值(game, 目标实体, 情绪类型, 变化量):
    """修改目标实体的指定类型情绪值

    - 变化量为正数表示增加，负数表示减少
    - 情绪值会被自动限制在0和上限之间
    - 当情绪达到上限时，标记为过载状态
    """
    var_name = f"情绪_{情绪类型}"
    max_var_name = f"情绪上限_{情绪类型}"
    overload_var_name = f"情绪过载_{情绪类型}"

    current_value = game.get_custom_variable(目标实体, var_name, 0)
    emotion_max = game.get_custom_variable(目标实体, max_var_name, 8)

    new_value = max(0, min(emotion_max, current_value + 变化量))
    game.set_custom_variable(目标实体, var_name, new_value, True)

    # 判断是否触发过载（达到上限）
    is_overload = new_value >= emotion_max
    if is_overload:
        game.set_custom_variable(目标实体, overload_var_name, True, True)
        log_info(f"[修改情绪值] {情绪类型}: {current_value} + {变化量} = {new_value}/{emotion_max}, 触发过载!")
    else:
        log_info(f"[修改情绪值] {情绪类型}: {current_value} + {变化量} = {new_value}/{emotion_max}")

    return new_value, is_overload
