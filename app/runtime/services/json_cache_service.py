from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

from engine.utils.cache.cache_paths import get_runtime_cache_root

_DEFAULT_JSON_INDENT = 2
_DEFAULT_KV_SCHEMA_VERSION = 1


class JsonCacheService:
    """运行期 JSON 缓存门面（无 PyQt6 依赖）。

    目标：
    - UI/控制器层不再自行拼 cache 路径、不再自行读写 JSON；
    - 统一使用 runtime_cache_root（支持 settings.RUNTIME_CACHE_ROOT 重定向）；
    - 所有写入均使用“写 tmp -> replace”的原子写策略，避免中断产生半写入文件。
    """

    def __init__(self, workspace_path: Path) -> None:
        self.workspace_path = workspace_path
        self.runtime_cache_root = get_runtime_cache_root(workspace_path)

    def resolve_cache_path(self, relative_path: str) -> Path:
        relative_path_obj = Path(relative_path)
        if relative_path_obj.is_absolute():
            raise ValueError(f"cache relative_path 不允许为绝对路径：{relative_path!r}")
        if ".." in relative_path_obj.parts:
            raise ValueError(f"cache relative_path 不允许包含上级目录：{relative_path!r}")
        return self.runtime_cache_root / relative_path_obj

    # --------------------------------------------------------------------- Document store (整文件读写)
    def load_json(self, relative_path: str) -> Any | None:
        cache_path = self.resolve_cache_path(relative_path)
        if not cache_path.exists():
            return None
        serialized_text = cache_path.read_text(encoding="utf-8")
        if not serialized_text.strip():
            return None
        return json.loads(serialized_text)

    def save_json(
        self,
        relative_path: str,
        payload: Any,
        *,
        ensure_ascii: bool = False,
        indent: int = _DEFAULT_JSON_INDENT,
        sort_keys: bool = True,
    ) -> None:
        cache_path = self.resolve_cache_path(relative_path)
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = cache_path.with_name(f"{cache_path.name}.tmp")
        serialized_text = json.dumps(
            payload,
            ensure_ascii=ensure_ascii,
            indent=int(indent),
            sort_keys=bool(sort_keys),
        )
        tmp_path.write_text(serialized_text, encoding="utf-8")
        tmp_path.replace(cache_path)

    def load_document_dict(self, relative_path: str) -> Optional[Dict[str, Any]]:
        loaded_payload = self.load_json(relative_path)
        if isinstance(loaded_payload, dict):
            return loaded_payload
        return None

    def save_document_dict(self, relative_path: str, payload: Dict[str, Any]) -> None:
        self.save_json(
            relative_path,
            payload,
            ensure_ascii=False,
            indent=_DEFAULT_JSON_INDENT,
            sort_keys=True,
        )

    def append_text(self, relative_path: str, text: str, *, encoding: str = "utf-8") -> None:
        if not isinstance(text, str):
            raise ValueError("append_text: text 必须为 str")
        cache_path = self.resolve_cache_path(relative_path)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with cache_path.open("a", encoding=str(encoding)) as file_obj:
            file_obj.write(text)

    def append_jsonl(
        self,
        relative_path: str,
        payload: Any,
        *,
        ensure_ascii: bool = False,
        sort_keys: bool = False,
    ) -> None:
        serialized_line = json.dumps(
            payload,
            ensure_ascii=ensure_ascii,
            sort_keys=bool(sort_keys),
        )
        self.append_text(relative_path, serialized_line + "\n")

    # --------------------------------------------------------------------- KV store（标准化的小型键值存储）
    def get_kv_value(self, relative_path: str, key: str, default: Any = None) -> Any:
        if not isinstance(key, str) or not key.strip():
            raise ValueError("KV key 必须为非空字符串")
        kv_payload = self._load_kv_payload(relative_path)
        values_payload = kv_payload.get("values")
        if not isinstance(values_payload, dict):
            return default
        if key in values_payload:
            return values_payload[key]
        return default

    def get_kv_str(self, relative_path: str, key: str, default: str = "") -> str:
        raw_value = self.get_kv_value(relative_path, key, default=default)
        if isinstance(raw_value, str):
            return raw_value.strip()
        return default

    def set_kv_value(self, relative_path: str, key: str, value: Any) -> None:
        if not isinstance(key, str) or not key.strip():
            raise ValueError("KV key 必须为非空字符串")
        kv_payload = self._load_kv_payload(relative_path)
        values_payload = kv_payload.get("values")
        if not isinstance(values_payload, dict):
            values_payload = {}
            kv_payload["values"] = values_payload

        if value is None:
            values_payload.pop(key, None)
        else:
            values_payload[key] = value

        self._save_kv_payload(relative_path, kv_payload)

    def set_kv_str(self, relative_path: str, key: str, value: str) -> None:
        if not isinstance(value, str):
            raise ValueError("KV str value 必须为字符串")
        self.set_kv_value(relative_path, key, value)

    def delete_kv_key(self, relative_path: str, key: str) -> None:
        self.set_kv_value(relative_path, key, None)

    def _load_kv_payload(self, relative_path: str) -> Dict[str, Any]:
        loaded_payload = self.load_json(relative_path)
        if loaded_payload is None:
            return {"schema_version": _DEFAULT_KV_SCHEMA_VERSION, "values": {}}
        if not isinstance(loaded_payload, dict):
            return {"schema_version": _DEFAULT_KV_SCHEMA_VERSION, "values": {}}

        values_payload = loaded_payload.get("values")
        if isinstance(values_payload, dict):
            schema_version = loaded_payload.get("schema_version", _DEFAULT_KV_SCHEMA_VERSION)
            if not isinstance(schema_version, int):
                schema_version = _DEFAULT_KV_SCHEMA_VERSION
            return {"schema_version": int(schema_version), "values": values_payload}

        # 兼容：旧版 `player_ingame_save_selection.json` 采用 {"player_template_last_selection": {...}} 存储
        legacy_mapping = loaded_payload.get("player_template_last_selection")
        if isinstance(legacy_mapping, dict):
            schema_version = loaded_payload.get("schema_version", _DEFAULT_KV_SCHEMA_VERSION)
            if not isinstance(schema_version, int):
                schema_version = _DEFAULT_KV_SCHEMA_VERSION
            return {"schema_version": int(schema_version), "values": dict(legacy_mapping)}

        return {"schema_version": _DEFAULT_KV_SCHEMA_VERSION, "values": {}}

    def _save_kv_payload(self, relative_path: str, kv_payload: Dict[str, Any]) -> None:
        schema_version_value = kv_payload.get("schema_version", _DEFAULT_KV_SCHEMA_VERSION)
        if not isinstance(schema_version_value, int):
            schema_version_value = _DEFAULT_KV_SCHEMA_VERSION

        values_payload = kv_payload.get("values")
        if not isinstance(values_payload, dict):
            values_payload = {}

        normalized_payload = {
            "schema_version": int(schema_version_value),
            "values": values_payload,
        }
        self.save_json(
            relative_path,
            normalized_payload,
            ensure_ascii=False,
            indent=_DEFAULT_JSON_INDENT,
            sort_keys=True,
        )


_SHARED_SERVICE_LOCK = Lock()
_SHARED_SERVICES: Dict[str, JsonCacheService] = {}


def get_shared_json_cache_service(workspace_path: Path) -> JsonCacheService:
    """按 workspace_path 维度缓存 JsonCacheService，避免多处重复创建。"""
    resolved_workspace = str(workspace_path.resolve())
    with _SHARED_SERVICE_LOCK:
        service = _SHARED_SERVICES.get(resolved_workspace)
        if service is None:
            service = JsonCacheService(workspace_path.resolve())
            _SHARED_SERVICES[resolved_workspace] = service
        return service


