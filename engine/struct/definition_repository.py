from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple


@dataclass(frozen=True)
class StructFieldDefinition:
    """结构体字段定义（只读视图）。"""

    field_name: str
    param_type: str
    default_value: Dict[str, Any] | None = None
    length: int | None = None


class StructDefinitionRepository:
    """基于 DefinitionSchemaView 的结构体定义只读仓库（严格 schema，无历史兼容分支）。

    职责：
    - 统一从代码级 Schema 视图加载 `{struct_id: payload}` 映射；
    - 提供按 ID / 显示名解析结构体的轻量接口；
    - 提供结构体字段集合视图，供解析器 / UI / 校验规则复用；
    - 在仓库边界处执行 schema 校验，杜绝各处自行解析与兼容旧字段。
    """

    # 结构体定义 payload（STRUCT_PAYLOAD）允许的顶层字段集合（严格）
    _ALLOWED_PAYLOAD_KEYS: Set[str] = {"type", "struct_type", "struct_name", "fields"}
    # 字段定义允许字段集合（严格）
    _ALLOWED_FIELD_KEYS: Set[str] = {"field_name", "param_type", "default_value", "length"}
    # 明确禁止的历史字段（用于给出更可读的错误）
    _BANNED_LEGACY_KEYS: Set[str] = {"struct_ype", "name", "value", "members"}
    _BANNED_LEGACY_FIELD_KEYS: Set[str] = {"key", "lenth"}

    def __init__(self) -> None:
        # 延迟导入 DefinitionSchemaView，避免在引擎初始化早期引入
        # `engine.resources` → `GlobalResourceView` → `engine.struct` 的循环依赖。
        module = import_module("engine.resources.definition_schema_view")
        get_schema_view = getattr(module, "get_default_definition_schema_view")
        self._schema_view = get_schema_view()
        self._all_payloads: Dict[str, Dict[str, Any]] | None = None
        self._id_by_name: Dict[str, str] | None = None
        self._fields_by_id: Dict[str, List[StructFieldDefinition]] | None = None

    def invalidate_cache(self) -> None:
        """使仓库内派生缓存失效。"""
        self._all_payloads = None
        self._id_by_name = None
        self._fields_by_id = None

    @staticmethod
    def _safe_str(value: object) -> str:
        return str(value).strip() if isinstance(value, str) else ""

    def _validate_payload_schema(self, struct_id: str, payload: Mapping[str, Any]) -> None:
        if not isinstance(payload, Mapping):
            raise ValueError(f"结构体定义 payload 非 dict: {struct_id}")

        # 顶层字段：严格 + 显式禁止历史字段
        payload_keys = set(payload.keys())
        legacy_hits = sorted(k for k in payload_keys if k in self._BANNED_LEGACY_KEYS)
        if legacy_hits:
            raise ValueError(
                f"结构体定义包含已废弃字段（不再兼容）：{struct_id} -> {legacy_hits}"
            )
        unknown = sorted(k for k in payload_keys if k not in self._ALLOWED_PAYLOAD_KEYS)
        if unknown:
            raise ValueError(f"结构体定义包含未知字段：{struct_id} -> {unknown}")

        type_value = payload.get("type")
        if type_value != "Struct":
            raise ValueError(
                f"结构体定义.type 必须为 'Struct'：{struct_id} -> {type_value!r}"
            )

        struct_type = payload.get("struct_type")
        if not isinstance(struct_type, str) or not struct_type.strip():
            raise ValueError(f"结构体定义.struct_type 必须为非空字符串：{struct_id}")

        struct_name = payload.get("struct_name")
        if not isinstance(struct_name, str) or not struct_name.strip():
            raise ValueError(f"结构体定义.struct_name 必须为非空字符串：{struct_id}")

        fields_value = payload.get("fields")
        if not isinstance(fields_value, Sequence) or isinstance(fields_value, (str, bytes)):
            raise ValueError(f"结构体定义.fields 必须为列表：{struct_id}")

        for index, entry in enumerate(fields_value):
            if not isinstance(entry, Mapping):
                raise ValueError(f"结构体定义.fields[{index}] 不是 dict：{struct_id}")
            entry_keys = set(entry.keys())
            legacy_field_hits = sorted(
                k for k in entry_keys if k in self._BANNED_LEGACY_FIELD_KEYS
            )
            if legacy_field_hits:
                raise ValueError(
                    f"结构体定义字段包含已废弃字段（不再兼容）：{struct_id}.fields[{index}] -> {legacy_field_hits}"
                )
            unknown_field = sorted(k for k in entry_keys if k not in self._ALLOWED_FIELD_KEYS)
            if unknown_field:
                raise ValueError(
                    f"结构体定义字段包含未知字段：{struct_id}.fields[{index}] -> {unknown_field}"
                )

            field_name = entry.get("field_name")
            if not isinstance(field_name, str) or not field_name.strip():
                raise ValueError(f"结构体字段.field_name 必须为非空字符串：{struct_id}.fields[{index}]")

            param_type = entry.get("param_type")
            if not isinstance(param_type, str) or not param_type.strip():
                raise ValueError(f"结构体字段.param_type 必须为非空字符串：{struct_id}.fields[{index}]")

            length = entry.get("length")
            if length is not None and not isinstance(length, int):
                raise ValueError(
                    f"结构体字段.length 必须为 int 或省略：{struct_id}.fields[{index}] -> {length!r}"
                )

            default_value = entry.get("default_value")
            if default_value is not None and not isinstance(default_value, Mapping):
                raise ValueError(
                    f"结构体字段.default_value 必须为 dict 或省略：{struct_id}.fields[{index}]"
                )

    def _materialize_payloads(self) -> None:
        if self._all_payloads is not None:
            return
        raw = self._schema_view.get_all_struct_definitions() or {}
        payloads: Dict[str, Dict[str, Any]] = {}
        for key, payload in raw.items():
            if not isinstance(key, str):
                continue
            struct_id = key.strip()
            if not struct_id:
                continue
            if not isinstance(payload, dict):
                raise ValueError(f"结构体定义 payload 非 dict: {struct_id}")
            self._validate_payload_schema(struct_id, payload)
            payloads[struct_id] = dict(payload)
        self._all_payloads = payloads

    def get_all_payloads(self) -> Dict[str, Dict[str, Any]]:
        """返回 {struct_id: payload} 的浅拷贝视图（payload 为 dict 副本）。"""
        self._materialize_payloads()
        if self._all_payloads is None:
            return {}
        return {struct_id: dict(payload) for struct_id, payload in self._all_payloads.items()}

    def get_payload(self, struct_id: str) -> Optional[Dict[str, Any]]:
        """按 ID 获取单个结构体定义 payload 的副本，未找到时返回 None。"""
        text = str(struct_id or "").strip()
        if not text:
            return None
        payload = self.get_all_payloads().get(text)
        if payload is None:
            return None
        return dict(payload)

    def _ensure_name_index(self) -> None:
        if self._id_by_name is not None:
            return
        self._id_by_name = {}
        for struct_id, payload in self.get_all_payloads().items():
            name_value = payload.get("struct_name")
            if not isinstance(name_value, str):
                continue
            text = name_value.strip()
            if not text:
                continue
            if text in self._id_by_name:
                existing = self._id_by_name[text]
                raise ValueError(
                    f"结构体定义 struct_name 重复：{text!r} -> {existing!r} / {struct_id!r}"
                )
            self._id_by_name[text] = struct_id

    def resolve_id_by_name(self, struct_name: str) -> str:
        """根据显示名称解析结构体 ID，解析失败返回空字符串。"""
        text = str(struct_name or "").strip()
        if not text:
            return ""
        self._ensure_name_index()
        if self._id_by_name is None:
            return ""
        struct_id = self._id_by_name.get(text)
        if struct_id is None:
            return ""
        return struct_id

    def _ensure_fields_index(self) -> None:
        if self._fields_by_id is not None:
            return
        fields_by_id: Dict[str, List[StructFieldDefinition]] = {}
        for struct_id, payload in self.get_all_payloads().items():
            fields_value = payload.get("fields") or []
            if not isinstance(fields_value, Sequence) or isinstance(fields_value, (str, bytes)):
                fields_by_id[struct_id] = []
                continue
            fields: List[StructFieldDefinition] = []
            for entry in fields_value:
                if not isinstance(entry, Mapping):
                    continue
                field_name = self._safe_str(entry.get("field_name"))
                param_type = self._safe_str(entry.get("param_type"))
                if not field_name or not param_type:
                    continue
                default_value_raw = entry.get("default_value")
                default_value = dict(default_value_raw) if isinstance(default_value_raw, Mapping) else None
                length_value = entry.get("length")
                length = int(length_value) if isinstance(length_value, int) else None
                fields.append(
                    StructFieldDefinition(
                        field_name=field_name,
                        param_type=param_type,
                        default_value=default_value,
                        length=length,
                    )
                )
            fields_by_id[struct_id] = fields
        self._fields_by_id = fields_by_id

    def get_fields(self, struct_id: str) -> List[StructFieldDefinition]:
        """返回结构体字段定义列表（保持定义顺序），未找到返回空列表。"""
        text = str(struct_id or "").strip()
        if not text:
            return []
        self._ensure_fields_index()
        if self._fields_by_id is None:
            return []
        return list(self._fields_by_id.get(text) or [])

    def get_field_names(self, struct_id: str) -> List[str]:
        return [field.field_name for field in self.get_fields(struct_id)]

    def get_struct_type(self, struct_id: str) -> str:
        payload = self.get_payload(struct_id) or {}
        raw = payload.get("struct_type")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        return ""

    def is_basic(self, struct_id: str) -> bool:
        return self.get_struct_type(struct_id) == "basic"


_default_repo: StructDefinitionRepository | None = None


def get_default_struct_repository() -> StructDefinitionRepository:
    """获取进程级默认的结构体定义仓库实例。"""
    global _default_repo
    if _default_repo is None:
        _default_repo = StructDefinitionRepository()
    return _default_repo


def invalidate_default_struct_repository_cache() -> None:
    """使进程级默认结构体仓库的二级缓存失效。"""
    global _default_repo
    if _default_repo is not None:
        _default_repo.invalidate_cache()


