from __future__ import annotations

from engine.nodes.node_definition_loader import NodeDef

from app.ui.controllers.graph_editor_flow.new_node_ports_policy import (
    derive_initial_input_names_for_new_node,
)


def test_new_node_default_inputs_passthrough() -> None:
    node_def = NodeDef(
        name="任意节点",
        category="运算节点",
        inputs=["流程入", "A", "B"],
        outputs=["流程出", "Out"],
    )
    assert derive_initial_input_names_for_new_node(node_def) == ["流程入", "A", "B"]


def test_new_node_assemble_dict_initial_ports_are_concretized() -> None:
    node_def = NodeDef(
        name="拼装字典",
        category="运算节点",
        inputs=["流程入", "键0~49", "值0~49"],
        outputs=["流程出", "结果"],
    )
    assert derive_initial_input_names_for_new_node(node_def) == ["键0", "值0"]


def test_new_node_assemble_dict_fallback_when_inputs_not_range_definitions() -> None:
    node_def = NodeDef(
        name="拼装字典",
        category="运算节点",
        inputs=["流程入", "键", "值"],
        outputs=["流程出", "结果"],
    )
    assert derive_initial_input_names_for_new_node(node_def) == ["流程入", "键", "值"]


