from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence


STRUCT_BINDINGS_METADATA_KEY: str = "struct_bindings"


@dataclass(frozen=True)
class StructBinding:
    """结构体绑定记录（GraphModel.metadata[struct_bindings][node_id]）。"""

    struct_id: str
    struct_name: str
    field_names: List[str]


_ALLOWED_STRUCT_BINDING_KEYS = {"struct_id", "struct_name", "field_names"}


def normalize_struct_binding_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """将任意 mapping 规范化为严格的结构体绑定 payload（无历史兼容分支）。

    约定：
    - 必须包含 struct_id / struct_name / field_names 三个字段；
    - field_names 必须为 list[str]（允许空列表，表示“使用全部字段”）。
    """
    if not isinstance(payload, Mapping):
        raise ValueError("struct_bindings payload 必须为 dict")

    keys = set(payload.keys())
    unknown = sorted(k for k in keys if k not in _ALLOWED_STRUCT_BINDING_KEYS)
    if unknown:
        raise ValueError(f"struct_bindings payload 包含未知字段：{unknown}")

    struct_id_value = payload.get("struct_id")
    if not isinstance(struct_id_value, str) or not struct_id_value.strip():
        raise ValueError("struct_bindings.struct_id 必须为非空字符串")
    struct_id = struct_id_value.strip()

    struct_name_value = payload.get("struct_name")
    if not isinstance(struct_name_value, str) or not struct_name_value.strip():
        raise ValueError("struct_bindings.struct_name 必须为非空字符串")
    struct_name = struct_name_value.strip()

    field_names_value = payload.get("field_names")
    if not isinstance(field_names_value, Sequence) or isinstance(field_names_value, (str, bytes)):
        raise ValueError("struct_bindings.field_names 必须为字符串列表")

    normalized_field_names: List[str] = []
    for entry in field_names_value:
        if not isinstance(entry, str):
            raise ValueError("struct_bindings.field_names 必须为字符串列表")
        text = entry.strip()
        if not text:
            raise ValueError("struct_bindings.field_names 不允许出现空字符串")
        if text not in normalized_field_names:
            normalized_field_names.append(text)

    return {
        "struct_id": struct_id,
        "struct_name": struct_name,
        "field_names": normalized_field_names,
    }


def normalize_struct_bindings_map(struct_bindings: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """规范化 struct_bindings 映射（用于批量校验与回写）。"""
    if not isinstance(struct_bindings, Mapping):
        raise ValueError("metadata[struct_bindings] 必须为 dict")

    normalized: Dict[str, Dict[str, Any]] = {}
    for node_id_raw, payload in struct_bindings.items():
        if not isinstance(node_id_raw, str) or not node_id_raw.strip():
            raise ValueError("struct_bindings 的 key（node_id）必须为非空字符串")
        node_id = node_id_raw.strip()
        if not isinstance(payload, Mapping):
            raise ValueError(f"struct_bindings[{node_id}] 必须为 dict")
        normalized[node_id] = normalize_struct_binding_payload(payload)
    return normalized


