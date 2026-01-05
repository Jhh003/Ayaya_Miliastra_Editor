from __future__ import annotations
from engine.nodes.node_spec import node_spec
from plugins.nodes.shared.server_查询节点_impl_helpers import *
from engine.utils.logging.logger import log_info


@node_spec(
    name="获取物质核心",
    category="查询节点",
    inputs=[("目标实体", "实体")],
    outputs=[("物质核心", "整数"), ("上限", "整数")],
    description="获取目标实体的当前物质核心(MC)值和上限。物质核心是天工部-物质匠师的核心资源，用于修改武器属性。",
    doc_reference="服务器节点/查询节点/九权天部.md"
)
def 获取物质核心(game, 目标实体):
    """获取目标实体的当前物质核心(MC)值和上限

    物质核心是天工部-物质匠师的核心资源：
    - 攻击敌人或破坏环境获得物质核心
    - 消耗物质核心可修改自身武器属性
    - 默认上限为8点
    """
    mc = game.get_custom_variable(目标实体, "物质核心", 0)
    mc_max = game.get_custom_variable(目标实体, "物质核心上限", 8)
    log_info(f"[获取物质核心] 实体物质核心: {mc}/{mc_max}")
    return mc, mc_max
