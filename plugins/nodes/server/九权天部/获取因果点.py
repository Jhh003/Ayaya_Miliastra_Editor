from __future__ import annotations
from engine.nodes.node_spec import node_spec
from plugins.nodes.shared.server_查询节点_impl_helpers import *
from engine.utils.logging.logger import log_info


@node_spec(
    name="获取因果点",
    category="查询节点",
    inputs=[("目标实体", "实体")],
    outputs=[("因果点", "整数"), ("上限", "整数")],
    description="获取目标实体的当前因果点(CP)值和上限。因果点是钦天监-因果命师的核心资源，用于触发必然效果。",
    doc_reference="服务器节点/查询节点/九权天部.md"
)
def 获取因果点(game, 目标实体):
    """获取目标实体的当前因果点(CP)值和上限

    因果点是钦天监-因果命师的核心资源：
    - 攻击命中时有概率获得因果点
    - 消耗因果点可触发必然效果（如必然暴击）
    - 默认上限为10点
    """
    cp = game.get_custom_variable(目标实体, "因果点", 0)
    cp_max = game.get_custom_variable(目标实体, "因果点上限", 10)
    log_info(f"[获取因果点] 实体因果点: {cp}/{cp_max}")
    return cp, cp_max
