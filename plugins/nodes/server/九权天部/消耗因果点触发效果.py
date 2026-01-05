from __future__ import annotations
from engine.nodes.node_spec import node_spec
from plugins.nodes.shared.server_执行节点_impl_helpers import *
from engine.utils.logging.logger import log_info


@node_spec(
    name="消耗因果点触发效果",
    category="执行节点",
    inputs=[
        ("流程入", "流程"),
        ("目标实体", "实体"),
        ("消耗量", "整数"),
        ("效果类型", "字符串"),
    ],
    outputs=[
        ("流程出", "流程"),
        ("触发成功", "布尔值"),
        ("剩余因果点", "整数"),
    ],
    description="消耗指定数量的因果点触发必然效果。效果类型包括：必然暴击、必然闪避、必然命中等。",
    doc_reference="服务器节点/执行节点/九权天部.md",
    input_enum_options={
        "效果类型": ["必然暴击", "必然闪避", "必然命中", "必然触发特效"],
    },
)
def 消耗因果点触发效果(game, 目标实体, 消耗量, 效果类型):
    """消耗因果点触发必然效果

    必然效果类型：
    - 必然暴击：下次攻击必定暴击
    - 必然闪避：下次被攻击必定闪避
    - 必然命中：下次攻击必定命中
    - 必然触发特效：下次攻击必定触发武器特效

    返回触发是否成功以及剩余因果点
    """
    current_cp = game.get_custom_variable(目标实体, "因果点", 0)

    if current_cp < 消耗量:
        log_info(f"[消耗因果点触发效果] 因果点不足: {current_cp}/{消耗量}，触发失败")
        return False, current_cp

    # 消耗因果点
    new_cp = current_cp - 消耗量
    game.set_custom_variable(目标实体, "因果点", new_cp, True)

    # 设置必然效果标记
    effect_var_name = f"因果效果_{效果类型}"
    game.set_custom_variable(目标实体, effect_var_name, True, True)

    log_info(f"[消耗因果点触发效果] 消耗{消耗量}点因果点，触发{效果类型}，剩余{new_cp}")
    return True, new_cp
