from __future__ import annotations

from typing import List

from app.models.todo_item import TodoItem
from app.ui.todo.todo_detail_builder_registry import (
    TodoDetailBuildContext,
    register_detail_type,
)
from app.ui.todo.detail_builders.shared_builders import (
    DetailDocument,
    DetailSection,
    ParagraphBlock,
    ParagraphStyle,
    TableBlock,
    build_simple_title_and_description_document,
)


@register_detail_type("template_graph_root")
@register_detail_type("event_flow_root")
@register_detail_type("graph_create_node")
@register_detail_type("graph_create_and_connect")
@register_detail_type("graph_create_and_connect_reverse")
def build_simple_graph_step_document(
    _context: TodoDetailBuildContext,
    todo: TodoItem,
    _info: dict,
    _detail_type: str,
) -> DetailDocument:
    return build_simple_title_and_description_document(todo)


@register_detail_type("graph_config_node_merged")
def build_graph_config_node_document(
    _context: TodoDetailBuildContext,
    todo: TodoItem,
    info: dict,
    _detail_type: str,
) -> DetailDocument:
    document = DetailDocument()
    section = DetailSection(title=str(todo.title), level=3)

    node_title = str(info.get("node_title", ""))
    section.blocks.append(
        ParagraphBlock(text=f"节点：{node_title}", style=ParagraphStyle.EMPHASIS)
    )

    parameters = info.get("params", [])
    if parameters:
        headers = ["参数", "值"]
        rows: List[List[str]] = []
        for parameter_information in parameters:
            rows.append(
                [
                    str(parameter_information.get("param_name", "")),
                    str(parameter_information.get("param_value", "")),
                ]
            )
        section.blocks.append(TableBlock(headers=headers, rows=rows))

    document.sections.append(section)
    return document


@register_detail_type("graph_config_branch_outputs")
def build_graph_config_branch_outputs_document(
    _context: TodoDetailBuildContext,
    todo: TodoItem,
    info: dict,
    _detail_type: str,
) -> DetailDocument:
    document = DetailDocument()
    section = DetailSection(title=str(todo.title), level=3)

    node_title = str(info.get("node_title", ""))
    section.blocks.append(
        ParagraphBlock(text=f"节点：{node_title}", style=ParagraphStyle.EMPHASIS)
    )

    branch_list = info.get("branches", [])
    if branch_list:
        headers = ["分支端口", "匹配值"]
        rows: List[List[str]] = []
        for branch in branch_list:
            rows.append([str(branch.get("port_name", "")), str(branch.get("value", ""))])
        section.blocks.append(TableBlock(headers=headers, rows=rows))

    document.sections.append(section)
    return document


@register_detail_type("graph_connect_merged")
def build_graph_connect_merged_document(
    _context: TodoDetailBuildContext,
    todo: TodoItem,
    info: dict,
    _detail_type: str,
) -> DetailDocument:
    document = DetailDocument()
    section = DetailSection(title=str(todo.title), level=3)

    node_title_one = str(info.get("node1_title", ""))
    node_title_two = str(info.get("node2_title", ""))
    if node_title_one or node_title_two:
        section.blocks.append(
            ParagraphBlock(
                text=f"{node_title_one} → {node_title_two}",
                style=ParagraphStyle.EMPHASIS,
            )
        )

    edge_list = info.get("edges", [])
    if edge_list:
        headers = ["源端口", "目标端口"]
        rows: List[List[str]] = []
        for edge in edge_list:
            rows.append([str(edge.get("src_port", "")), str(edge.get("dst_port", ""))])
        section.blocks.append(TableBlock(headers=headers, rows=rows))

    document.sections.append(section)
    return document


@register_detail_type("graph_signals_overview")
def build_graph_signals_overview_document(
    _context: TodoDetailBuildContext,
    _todo: TodoItem,
    info: dict,
    _detail_type: str,
) -> DetailDocument:
    document = DetailDocument()
    section = DetailSection(title="本图信号概览", level=3)

    graph_name = str(info.get("graph_name", "") or "")
    if graph_name:
        section.blocks.append(
            ParagraphBlock(
                text=f"节点图：{graph_name}",
                style=ParagraphStyle.EMPHASIS,
            )
        )

    signal_entries = info.get("signals", []) or []
    if signal_entries:
        headers = ["信号名", "信号ID", "使用节点数", "是否在当前存档定义"]
        rows: List[List[str]] = []
        for entry in signal_entries:
            signal_name = entry.get("signal_name") or "(未命名信号)"
            signal_identifier = entry.get("signal_id") or ""
            node_count = int(entry.get("node_count", 0))
            defined = bool(entry.get("defined_in_package", False))
            defined_text = "是" if defined else "否"
            rows.append(
                [
                    str(signal_name),
                    str(signal_identifier),
                    str(node_count),
                    defined_text,
                ]
            )
        section.blocks.append(TableBlock(headers=headers, rows=rows))
        section.blocks.append(
            ParagraphBlock(
                text="双击任务或使用右上角按钮可在编辑器中查看并调整这些信号节点。",
                style=ParagraphStyle.HINT,
            )
        )

    document.sections.append(section)
    return document


@register_detail_type("graph_bind_signal")
def build_graph_bind_signal_document(
    _context: TodoDetailBuildContext,
    todo: TodoItem,
    info: dict,
    _detail_type: str,
) -> DetailDocument:
    document = DetailDocument()
    section = DetailSection(title=str(todo.title), level=3)

    node_title = str(info.get("node_title", ""))
    node_identifier = str(info.get("node_id", ""))
    if node_title or node_identifier:
        target_text_parts: List[str] = []
        if node_title:
            target_text_parts.append(node_title)
        if node_identifier:
            target_text_parts.append(f"({node_identifier})")
        section.blocks.append(
            ParagraphBlock(
                text="目标节点：" + " ".join(target_text_parts),
                style=ParagraphStyle.EMPHASIS,
            )
        )

    signal_name = str(info.get("signal_name") or "")
    signal_identifier = str(info.get("signal_id") or "")
    if signal_name or signal_identifier:
        signal_text_parts: List[str] = []
        if signal_name:
            signal_text_parts.append(signal_name)
        if signal_identifier:
            signal_text_parts.append(f"({signal_identifier})")
        section.blocks.append(
            ParagraphBlock(
                text="当前绑定信号：" + " ".join(signal_text_parts),
                style=ParagraphStyle.NORMAL,
            )
        )
    else:
        section.blocks.append(
            ParagraphBlock(
                text="当前绑定信号：未选择",
                style=ParagraphStyle.HINT,
            )
        )

    section.blocks.append(
        ParagraphBlock(
            text=(
                "在节点图中右键该节点，可通过“选择信号…”绑定信号，"
                "或通过“打开信号管理器…”调整信号定义。"
            ),
            style=ParagraphStyle.HINT,
        )
    )

    document.sections.append(section)
    return document


@register_detail_type("graph_bind_struct")
def build_graph_bind_struct_document(
    _context: TodoDetailBuildContext,
    todo: TodoItem,
    info: dict,
    _detail_type: str,
) -> DetailDocument:
    document = DetailDocument()
    section = DetailSection(title=str(todo.title), level=3)

    node_title = str(info.get("node_title", ""))
    node_identifier = str(info.get("node_id", ""))
    if node_title or node_identifier:
        target_text_parts: List[str] = []
        if node_title:
            target_text_parts.append(node_title)
        if node_identifier:
            target_text_parts.append(f"({node_identifier})")
        section.blocks.append(
            ParagraphBlock(
                text="目标节点：" + " ".join(target_text_parts),
                style=ParagraphStyle.EMPHASIS,
            )
        )

    struct_name = str(info.get("struct_name") or "")
    struct_identifier = str(info.get("struct_id") or "")
    if struct_name or struct_identifier:
        struct_text_parts: List[str] = []
        if struct_name:
            struct_text_parts.append(struct_name)
        if struct_identifier:
            struct_text_parts.append(f"({struct_identifier})")
        section.blocks.append(
            ParagraphBlock(
                text="当前绑定结构体：" + " ".join(struct_text_parts),
                style=ParagraphStyle.NORMAL,
            )
        )
    else:
        section.blocks.append(
            ParagraphBlock(
                text="当前绑定结构体：未选择",
                style=ParagraphStyle.HINT,
            )
        )

    field_names = info.get("field_names") or []
    if isinstance(field_names, list) and field_names:
        field_names_text = "、".join(str(name) for name in field_names)
        section.blocks.append(
            ParagraphBlock(
                text=f"已选字段：{field_names_text}",
                style=ParagraphStyle.NORMAL,
            )
        )

    section.blocks.append(
        ParagraphBlock(
            text=(
                "在节点图中右键该节点，通过“配置结构体…”对话框选择结构体与字段；"
                "结构体名输入端口只作展示，不参与连线。"
            ),
            style=ParagraphStyle.HINT,
        )
    )

    document.sections.append(section)
    return document


