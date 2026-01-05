from __future__ import annotations
from engine.nodes.node_spec import node_spec
from plugins.nodes.shared.server_执行节点_impl_helpers import *
from engine.utils.logging.logger import log_info


@node_spec(
    name="设置物质核心上限",
    category="执行节点",
    inputs=[("流程入", "流程"), ("目标实体", "实体"), ("新上限", "整数")],
    outputs=[("流程出", "流程")],
    description="设置目标实体的物质核心(MC)上限。如果当前物质核心超过新上限，会被自动调整。",
    doc_reference="服务器节点/执行节点/九权天部.md"
)
def 设置物质核心上限(game, 目标实体, 新上限):
    """设置目标实体的物质核心(MC)上限

    - 上限最小为1
    - 如果当前物质核心超过新上限，会被自动调整为新上限
    - 可通过升级或道具提升上限
    """
    new_max = max(1, 新上限)
    game.set_custom_variable(目标实体, "物质核心上限", new_max, True)

    # 如果当前值超过新上限，调整当前值
    current_mc = game.get_custom_variable(目标实体, "物质核心", 0)
    if current_mc > new_max:
        game.set_custom_variable(目标实体, "物质核心", new_max, True)
        log_info(f"[设置物质核心上限] 上限设为{new_max}，当前值从{current_mc}调整为{new_max}")
    else:
        log_info(f"[设置物质核心上限] 上限设为{new_max}")
