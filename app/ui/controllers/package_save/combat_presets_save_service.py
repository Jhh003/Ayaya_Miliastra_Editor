"""战斗预设保存服务：将 PackageView.combat_presets 写回资源库与 PackageIndex。"""

from __future__ import annotations

from engine.resources.package_index import PackageIndex
from engine.resources.package_view import PackageView
from engine.resources.resource_manager import ResourceManager, ResourceType


class CombatPresetsSaveService:
    def __init__(self, resource_manager: ResourceManager):
        self._resource_manager = resource_manager

    def save_preset_resources(
        self,
        *,
        package: object,
        preset_keys: set[tuple[str, str]] | None,
    ) -> bool:
        """按需保存战斗预设资源本体（不修改 PackageIndex）。

        preset_keys:
            - None: 保存当前视图中可见的全部战斗预设资源（谨慎使用）
            - set[(section_key, item_id)]: 仅保存指定条目
        """
        combat_presets_view = getattr(package, "combat_presets", None)
        if combat_presets_view is None:
            return False

        bucket_definitions = [
            ("player_template", "player_templates", ResourceType.PLAYER_TEMPLATE, "template_id"),
            ("player_class", "player_classes", ResourceType.PLAYER_CLASS, "class_id"),
            ("unit_status", "unit_statuses", ResourceType.UNIT_STATUS, "status_id"),
            ("skill", "skills", ResourceType.SKILL, "skill_id"),
            ("projectile", "projectiles", ResourceType.PROJECTILE, "projectile_id"),
            ("item", "items", ResourceType.ITEM, "item_id"),
        ]
        section_to_bucket: dict[str, tuple[str, ResourceType, str]] = {
            section_key: (bucket_key, resource_type, id_field)
            for section_key, bucket_key, resource_type, id_field in bucket_definitions
        }

        allowed_ids_by_bucket: dict[str, set[str]] | None = None
        if preset_keys is not None:
            allowed_ids_by_bucket = {}
            for section_key, item_id in preset_keys:
                if not section_key or not item_id:
                    continue
                mapped = section_to_bucket.get(section_key)
                if mapped is None:
                    continue
                bucket_key, _resource_type, _id_field = mapped
                allowed_ids_by_bucket.setdefault(bucket_key, set()).add(item_id)

        saved_any = False

        for section_key, bucket_key, resource_type, id_field in bucket_definitions:
            del section_key
            bucket_mapping_any = getattr(combat_presets_view, bucket_key, None)
            if not isinstance(bucket_mapping_any, dict):
                continue
            bucket_mapping = bucket_mapping_any

            if allowed_ids_by_bucket is None:
                target_ids = list(bucket_mapping.keys())
            else:
                target_ids = list(allowed_ids_by_bucket.get(bucket_key, set()))
                if not target_ids:
                    continue

            for preset_id in target_ids:
                if not isinstance(preset_id, str) or not preset_id:
                    continue
                payload_any = bucket_mapping.get(preset_id)
                if not isinstance(payload_any, dict):
                    continue

                payload = dict(payload_any)
                if "id" not in payload:
                    payload["id"] = preset_id
                specific_id_value = payload.get(id_field)
                if not isinstance(specific_id_value, str) or not specific_id_value:
                    payload[id_field] = preset_id

                self._resource_manager.save_resource(resource_type, preset_id, payload)
                saved_any = True

        return saved_any

    def sync_to_index(
        self,
        *,
        package: PackageView,
        package_index: PackageIndex,
        allowed_buckets: set[str] | None = None,
    ) -> None:
        """将 PackageView 中的战斗预设引用列表写回 PackageIndex.resources.combat_presets。

        注意：此方法**只更新索引引用列表**，不保存资源本体。
        资源本体保存应使用 `save_preset_resources(...)`，按条目增量写回以避免全量 I/O。
        """
        print(
            "[COMBAT-PRESETS] 开始写回战斗预设到索引：",
            f"package_id={package_index.package_id!r}",
        )
        combat_presets_view = getattr(package, "combat_presets", None)
        if combat_presets_view is None:
            print(
                "[COMBAT-PRESETS] 当前 PackageView 未提供 combat_presets 视图模型，"
                "将清空索引中的战斗预设引用列表。",
                f"package_id={package_index.package_id!r}",
            )
            package_index.resources.combat_presets = {
                "player_templates": [],
                "player_classes": [],
                "unit_statuses": [],
                "skills": [],
                "projectiles": [],
                "items": [],
            }
            return

        bucket_definitions = [
            ("player_templates", ResourceType.PLAYER_TEMPLATE, "template_id"),
            ("player_classes", ResourceType.PLAYER_CLASS, "class_id"),
            ("unit_statuses", ResourceType.UNIT_STATUS, "status_id"),
            ("skills", ResourceType.SKILL, "skill_id"),
            ("projectiles", ResourceType.PROJECTILE, "projectile_id"),
            ("items", ResourceType.ITEM, "item_id"),
        ]

        combat_index_lists = package_index.resources.combat_presets

        for bucket_key, resource_type, id_field in bucket_definitions:
            del resource_type
            del id_field
            if allowed_buckets is not None and bucket_key not in allowed_buckets:
                continue
            bucket_mapping_any = getattr(combat_presets_view, bucket_key, None)
            if not isinstance(bucket_mapping_any, dict):
                print(
                    "[COMBAT-PRESETS] bucket 映射不是字典或为空，将写回空列表：",
                    f"package_id={package_index.package_id!r}, bucket_key={bucket_key!r}, "
                    f"actual_type={type(bucket_mapping_any).__name__}",
                )
                combat_index_lists[bucket_key] = []
                continue

            bucket_mapping = bucket_mapping_any
            print(
                "[COMBAT-PRESETS] bucket 写回前视图统计：",
                f"package_id={package_index.package_id!r}, bucket_key={bucket_key!r}, "
                f"preset_count={len(bucket_mapping)}",
            )
            new_ids: list[str] = []

            for preset_id in bucket_mapping.keys():
                if not isinstance(preset_id, str) or not preset_id:
                    continue
                new_ids.append(preset_id)

            new_ids.sort()
            combat_index_lists[bucket_key] = new_ids
            print(
                "[COMBAT-PRESETS] bucket 写回完成：",
                f"package_id={package_index.package_id!r}, bucket_key={bucket_key!r}, "
                f"saved_count={len(new_ids)}, index_ids={combat_index_lists[bucket_key]!r}",
            )


