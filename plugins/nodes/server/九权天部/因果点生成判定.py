from __future__ import annotations
from engine.nodes.node_spec import node_spec
from plugins.nodes.shared.server_查询节点_impl_helpers import *
from engine.utils.logging.logger import log_info


@node_spec(
    name="因果点生成判定",
    category="查询节点",
    inputs=[("目标实体", "实体"), ("基础概率", "浮点数"), ("连击加成", "浮点数")],
    outputs=[("是否获得", "布尔值"), ("获得数量", "整数")],
    description="判定攻击命中后是否获得因果点。基础概率默认10%，连续攻击同一目标时概率递增。",
    doc_reference="服务器节点/查询节点/九权天部.md"
)
def 因果点生成判定(game, 目标实体, 基础概率, 连击加成):
    """判定攻击命中后是否获得因果点

    生成机制：
    - 攻击命中时有基础概率获得1点CP
    - 连续攻击同一目标时，概率递增（连击加成）
    - 概率上限为100%

    参数说明：
    - 基础概率：默认0.1（10%）
    - 连击加成：每次连击增加的概率，默认0.05（5%）
    """
    # 获取连击计数
    combo_count = game.get_custom_variable(目标实体, "因果连击计数", 0)

    # 计算实际概率
    actual_prob = min(1.0, 基础概率 + 连击加成 * combo_count)

    # 随机判定
    roll = random.random()
    is_success = roll < actual_prob

    if is_success:
        log_info(f"[因果点生成判定] 判定成功! 概率{actual_prob*100:.1f}%，随机值{roll*100:.1f}%")
        return True, 1
    else:
        log_info(f"[因果点生成判定] 判定失败，概率{actual_prob*100:.1f}%，随机值{roll*100:.1f}%")
        return False, 0
