from __future__ import annotations
from engine.nodes.node_spec import node_spec
from plugins.nodes.shared.server_执行节点_impl_helpers import *
from engine.utils.logging.logger import log_info


@node_spec(
    name="修改物质核心",
    category="执行节点",
    inputs=[("流程入", "流程"), ("目标实体", "实体"), ("变化量", "整数")],
    outputs=[("流程出", "流程"), ("修改后物质核心", "整数"), ("是否达到上限", "布尔值")],
    description="修改目标实体的物质核心(MC)值。变化量可正可负，自动限制在0和上限之间。",
    doc_reference="服务器节点/执行节点/九权天部.md"
)
def 修改物质核心(game, 目标实体, 变化量):
    """修改目标实体的物质核心(MC)值

    - 变化量为正数表示增加，负数表示减少
    - 物质核心会被自动限制在0和上限之间
    - 返回修改后的物质核心值和是否达到上限
    """
    current_mc = game.get_custom_variable(目标实体, "物质核心", 0)
    mc_max = game.get_custom_variable(目标实体, "物质核心上限", 8)

    new_mc = max(0, min(mc_max, current_mc + 变化量))
    game.set_custom_variable(目标实体, "物质核心", new_mc, True)

    is_at_max = new_mc >= mc_max
    log_info(f"[修改物质核心] {current_mc} + {变化量} = {new_mc}/{mc_max}, 达到上限: {is_at_max}")
    return new_mc, is_at_max
