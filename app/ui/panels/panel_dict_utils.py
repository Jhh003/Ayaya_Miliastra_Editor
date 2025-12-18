"""面板内部通用的字典结构辅助函数。

目标：把“metadata 段落初始化 / dict-list 纠偏 / 默认结构补齐”从巨型面板中抽离，
减少重复样板代码，并让 UI 层更聚焦于渲染与交互。
"""

from __future__ import annotations

from typing import Any, Dict, List, MutableMapping, MutableSequence, TypeVar, cast


DictValue = Dict[str, Any]
ListValue = List[Any]

_TDict = TypeVar("_TDict", bound=MutableMapping[str, Any])
_TList = TypeVar("_TList", bound=MutableSequence[Any])


def ensure_dict_field(container: _TDict, key: str) -> DictValue:
    """确保 container[key] 为 dict，不是则创建空 dict 并写回。"""
    value = container.get(key)
    if isinstance(value, dict):
        return cast(DictValue, value)
    new_value: DictValue = {}
    container[key] = new_value
    return new_value


def ensure_list_field(container: _TDict, key: str) -> ListValue:
    """确保 container[key] 为 list，不是则创建空 list 并写回。"""
    value = container.get(key)
    if isinstance(value, list):
        return cast(ListValue, value)
    new_value: ListValue = []
    container[key] = new_value
    return new_value


def ensure_str_field(container: _TDict, key: str, default: str = "") -> str:
    """确保 container[key] 为 str，不是则写入 default 并返回 default。"""
    value = container.get(key)
    if isinstance(value, str):
        return value
    container[key] = default
    return default


def ensure_bool_field(container: _TDict, key: str, default: bool = False) -> bool:
    """确保 container[key] 为 bool，不是则写入 default 并返回 default。"""
    value = container.get(key)
    if isinstance(value, bool):
        return value
    container[key] = bool(default)
    return bool(default)


def ensure_int_field(container: _TDict, key: str, default: int = 0) -> int:
    """确保 container[key] 为 int（排除 bool），不是则写入 default 并返回 default。"""
    value = container.get(key)
    if isinstance(value, int) and not isinstance(value, bool):
        return int(value)
    container[key] = int(default)
    return int(default)


def ensure_float_field(container: _TDict, key: str, default: float = 0.0) -> float:
    """确保 container[key] 为 float 或 int（排除 bool），不是则写入 default 并返回 default。"""
    value = container.get(key)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    container[key] = float(default)
    return float(default)


def ensure_nested_dict(container: _TDict, *keys: str) -> DictValue:
    """确保 container 上按路径 keys 派生出的嵌套对象为 dict，并返回最后一级 dict。"""
    if not keys:
        raise ValueError("ensure_nested_dict 至少需要 1 个 key")
    current: MutableMapping[str, Any] = container
    for key in keys:
        value = current.get(key)
        if isinstance(value, dict):
            current = cast(MutableMapping[str, Any], value)
            continue
        new_value: DictValue = {}
        current[key] = new_value
        current = new_value
    return cast(DictValue, current)


def ensure_nested_list(container: _TDict, *keys: str) -> ListValue:
    """确保 container 上按路径 keys 派生出的嵌套对象为 list，并返回最后一级 list。"""
    if not keys:
        raise ValueError("ensure_nested_list 至少需要 1 个 key")
    if len(keys) == 1:
        return ensure_list_field(container, keys[0])
    parent = ensure_nested_dict(container, *keys[:-1])
    return ensure_list_field(cast(_TDict, parent), keys[-1])


