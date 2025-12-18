"""外部关卡变量（代码级 schema）加载器。

从 variables_tab.py 中拆出，减少 UI 层文件的领域逻辑体积。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from engine.graph.models.package_model import VariableConfig
from engine.resources.level_variable_schema_view import (
    get_default_level_variable_schema_view,
)


def load_external_variable_configs(reference_text: str) -> list[VariableConfig]:
    """从 LevelVariableSchemaView 中按引用字符串解析外部变量定义。

    匹配规则：
    - 精确匹配 source_path（归一化为 "/"）；
    - 或按文件名 stem 匹配（允许 metadata.custom_variable_file 只写不含扩展名的“ID 风格”）。
    """
    normalized_ref = str(reference_text).strip()
    if not normalized_ref:
        return []

    schema_view = get_default_level_variable_schema_view()
    all_variables = schema_view.get_all_variables()

    normalized_ref = normalized_ref.replace("\\", "/")

    results: list[VariableConfig] = []
    for payload in all_variables.values():
        if not isinstance(payload, dict):
            continue

        source_path_value = payload.get("source_path")
        source_stem_value = payload.get("source_stem")
        metadata_value = payload.get("metadata", {})

        source_candidates: list[str] = []

        if isinstance(source_path_value, str):
            source_candidates.append(source_path_value.strip())

        if isinstance(metadata_value, dict):
            metadata_source = metadata_value.get("source_path")
            if isinstance(metadata_source, str):
                source_candidates.append(metadata_source.strip())

        if isinstance(source_stem_value, str):
            source_candidates.append(source_stem_value.strip())

        matched = _match_reference(normalized_ref, source_candidates)
        if not matched:
            continue

        variable_config = _payload_to_variable_config(payload)
        if variable_config is None:
            continue
        results.append(variable_config)

    return results


def _match_reference(normalized_ref: str, candidates: list[str]) -> bool:
    for candidate in candidates:
        candidate_text = str(candidate).replace("\\", "/").strip()
        if not candidate_text:
            continue

        # 精确匹配完整相对路径（例如 自定义变量/forge_hero_player_template_variables.py）
        if candidate_text == normalized_ref:
            return True

        # 退化为仅按文件名（不含扩展名）匹配，允许 metadata.custom_variable_file 直接填写文件名 ID
        candidate_stem = Path(candidate_text).stem
        if candidate_stem == normalized_ref:
            return True

    return False


def _payload_to_variable_config(payload: Mapping[str, Any]) -> VariableConfig | None:
    name_value = payload.get("variable_name", payload.get("name", ""))
    type_value = payload.get("variable_type")
    default_value = payload.get("default_value")
    description_value = payload.get("description", "")

    if not isinstance(name_value, str) or not isinstance(type_value, str):
        return None

    return VariableConfig(
        name=name_value,
        variable_type=type_value,
        default_value=default_value,
        description=str(description_value) if description_value is not None else "",
    )


__all__ = ["load_external_variable_configs"]


