from __future__ import annotations
from engine.nodes.node_spec import node_spec
from plugins.nodes.shared.server_执行节点_impl_helpers import *
from engine.utils.logging.logger import log_info


@node_spec(
    name="设置情绪值上限",
    category="执行节点",
    inputs=[
        ("流程入", "流程"),
        ("目标实体", "实体"),
        ("情绪类型", "字符串"),
        ("新上限", "整数"),
    ],
    outputs=[("流程出", "流程")],
    description="设置目标实体指定类型情绪值的上限。如果当前情绪值超过新上限，会被自动调整。",
    doc_reference="服务器节点/执行节点/九权天部.md",
    input_enum_options={
        "情绪类型": ["愤怒", "恐惧", "绝望", "喜悦", "悲伤"],
    },
)
def 设置情绪值上限(game, 目标实体, 情绪类型, 新上限):
    """设置目标实体指定类型情绪值的上限

    - 上限最小为1
    - 如果当前情绪值超过新上限，会被自动调整为新上限
    """
    var_name = f"情绪_{情绪类型}"
    max_var_name = f"情绪上限_{情绪类型}"

    new_max = max(1, 新上限)
    game.set_custom_variable(目标实体, max_var_name, new_max, True)

    # 如果当前值超过新上限，调整当前值
    current_value = game.get_custom_variable(目标实体, var_name, 0)
    if current_value > new_max:
        game.set_custom_variable(目标实体, var_name, new_max, True)
        log_info(f"[设置情绪值上限] {情绪类型}上限设为{new_max}，当前值从{current_value}调整为{new_max}")
    else:
        log_info(f"[设置情绪值上限] {情绪类型}上限设为{new_max}")
