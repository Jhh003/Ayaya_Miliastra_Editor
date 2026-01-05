from __future__ import annotations
from engine.nodes.node_spec import node_spec
from plugins.nodes.shared.server_查询节点_impl_helpers import *
from engine.utils.logging.logger import log_info


@node_spec(
    name="获取情绪值",
    category="查询节点",
    inputs=[("目标实体", "实体"), ("情绪类型", "字符串")],
    outputs=[("情绪值", "整数"), ("上限", "整数"), ("是否过载", "布尔值")],
    description="获取目标实体的指定类型情绪值。情绪类型包括：愤怒、恐惧、绝望。",
    doc_reference="服务器节点/查询节点/九权天部.md",
    input_enum_options={
        "情绪类型": ["愤怒", "恐惧", "绝望", "喜悦", "悲伤"],
    },
)
def 获取情绪值(game, 目标实体, 情绪类型):
    """获取目标实体的指定类型情绪值

    情绪类型说明：
    - 愤怒：触发范围伤害效果
    - 恐惧：触发群体减速效果
    - 绝望：触发降低攻击力效果
    - 喜悦：触发自身增益效果（扩展）
    - 悲伤：触发敌人持续伤害效果（扩展）

    默认上限为8点，单一情绪达到上限时进入过载状态
    """
    var_name = f"情绪_{情绪类型}"
    max_var_name = f"情绪上限_{情绪类型}"

    emotion_value = game.get_custom_variable(目标实体, var_name, 0)
    emotion_max = game.get_custom_variable(目标实体, max_var_name, 8)
    is_overload = emotion_value >= emotion_max

    log_info(f"[获取情绪值] {情绪类型}: {emotion_value}/{emotion_max}, 过载: {is_overload}")
    return emotion_value, emotion_max, is_overload
