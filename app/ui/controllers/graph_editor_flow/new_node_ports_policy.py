from __future__ import annotations

from typing import Iterable

from engine.nodes.node_definition_loader import NodeDef
from engine.nodes.port_name_rules import parse_range_definition


FLOW_PORT_NAMES: set[str] = {"流程入", "流程出"}


def derive_initial_input_names_for_new_node(node_def: NodeDef) -> list[str]:
    """为“新建节点”推导更贴近实际使用的初始输入端口名列表。

    设计目标：
    - 控制器/场景不再硬编码业务特例（例如按节点名写 if/else）；
    - 规则集中于纯逻辑模块，可单测、可扩展；
    - 默认行为保持与 NodeDef.inputs 一致，仅对明确声明的特殊节点做优化。
    """
    declared_inputs: list[str] = [str(name) for name in (getattr(node_def, "inputs", None) or [])]

    if str(getattr(node_def, "name", "")) == "拼装字典":
        return _derive_initial_inputs_for_assemble_dict(declared_inputs)

    return declared_inputs


def _derive_initial_inputs_for_assemble_dict(declared_inputs: Iterable[str]) -> list[str]:
    """“拼装字典”节点的默认输入端口策略：

    - 该类节点通常用“键0~N/值0~N”的范围端口定义表达“键值对变参”；
    - 新建时直接给出一对 (键0, 值0) 更贴近用户的第一步操作。
    """
    data_inputs: list[str] = [str(name) for name in declared_inputs if str(name) not in FLOW_PORT_NAMES]
    if len(data_inputs) < 2:
        return [str(name) for name in declared_inputs]

    first_range = parse_range_definition(str(data_inputs[0]))
    second_range = parse_range_definition(str(data_inputs[1]))
    if first_range is None or second_range is None:
        return [str(name) for name in declared_inputs]

    key_prefix = str(first_range.get("prefix") or "")
    value_prefix = str(second_range.get("prefix") or "")
    start_index = int(first_range.get("start", 0))
    if not key_prefix or not value_prefix:
        return [str(name) for name in declared_inputs]

    return [
        f"{key_prefix}{start_index}",
        f"{value_prefix}{start_index}",
    ]


