"""复合节点源码格式探测与 payload 提取（单一事实来源）。

目标：
- 统一 loader / parser / validate 对“复合节点支持格式”的判定口径；
- 避免多处重复实现导致支持范围漂移；
- 不在此处做任何磁盘/导入副作用，保持纯逻辑。

支持格式：
- payload 格式：模块顶层存在 `COMPOSITE_PAYLOAD_JSON`（多行 JSON 字符串常量）
- 类格式：模块顶层存在带 `@composite_class` 装饰器的类
"""

from __future__ import annotations

import ast
import json
from typing import List, Optional

from engine.nodes.advanced_node_features import CompositeNodeConfig


def try_extract_composite_payload_json(tree: ast.Module) -> str | None:
    """从 AST 中提取模块顶层的 COMPOSITE_PAYLOAD_JSON 字符串常量。"""
    for stmt in tree.body:
        if not isinstance(stmt, ast.Assign):
            continue
        targets = getattr(stmt, "targets", None) or []
        if len(targets) != 1:
            continue
        target = targets[0]
        if not isinstance(target, ast.Name):
            continue
        if target.id != "COMPOSITE_PAYLOAD_JSON":
            continue
        value = getattr(stmt, "value", None)
        if isinstance(value, ast.Constant) and isinstance(getattr(value, "value", None), str):
            return value.value
    return None


def try_parse_composite_payload(tree: ast.Module) -> CompositeNodeConfig | None:
    """若存在 payload，则反序列化为 CompositeNodeConfig；否则返回 None。"""
    payload_json = try_extract_composite_payload_json(tree)
    if payload_json is None:
        return None

    payload_obj = json.loads(payload_json)
    if not isinstance(payload_obj, dict):
        raise ValueError("复合节点 JSON payload 格式错误：顶层必须为 dict")

    return CompositeNodeConfig.deserialize(payload_obj)


def _decorator_name(decorator: ast.AST) -> str:
    if isinstance(decorator, ast.Name):
        return decorator.id
    if isinstance(decorator, ast.Attribute):
        return decorator.attr
    if isinstance(decorator, ast.Call):
        return _decorator_name(decorator.func)
    return ""


def find_composite_classes(tree: ast.Module) -> List[ast.ClassDef]:
    """查找模块顶层所有带 @composite_class 的类。"""
    classes: List[ast.ClassDef] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for deco in node.decorator_list or []:
            if _decorator_name(deco) == "composite_class":
                classes.append(node)
                break
    return classes


def find_primary_composite_class(tree: ast.Module) -> Optional[ast.ClassDef]:
    """返回首个复合节点类（若存在）。"""
    classes = find_composite_classes(tree)
    if classes:
        return classes[0]
    return None


