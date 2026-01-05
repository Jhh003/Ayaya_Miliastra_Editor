from __future__ import annotations
from engine.nodes.node_spec import node_spec
from plugins.nodes.shared.server_执行节点_impl_helpers import *
from engine.utils.logging.logger import log_info


@node_spec(
    name="设置因果点上限",
    category="执行节点",
    inputs=[("流程入", "流程"), ("目标实体", "实体"), ("新上限", "整数")],
    outputs=[("流程出", "流程")],
    description="设置目标实体的因果点(CP)上限。如果当前因果点超过新上限，会被自动调整。",
    doc_reference="服务器节点/执行节点/九权天部.md"
)
def 设置因果点上限(game, 目标实体, 新上限):
    """设置目标实体的因果点(CP)上限

    - 上限最小为1
    - 如果当前因果点超过新上限，会被自动调整为新上限
    - 可通过升级或道具提升上限
    """
    new_max = max(1, 新上限)
    game.set_custom_variable(目标实体, "因果点上限", new_max, True)

    # 如果当前值超过新上限，调整当前值
    current_cp = game.get_custom_variable(目标实体, "因果点", 0)
    if current_cp > new_max:
        game.set_custom_variable(目标实体, "因果点", new_max, True)
        log_info(f"[设置因果点上限] 上限设为{new_max}，当前值从{current_cp}调整为{new_max}")
    else:
        log_info(f"[设置因果点上限] 上限设为{new_max}")
