"""
节点图代码严格验证器（引擎侧统一入口）

目标：
- 为“类结构节点图(.py)”提供按文件粒度的静态规则校验入口；
- 供 runtime/UI/CLI 等上层复用，避免上层各自实现校验分发与聚合。

说明：
- 校验规则与管线由 `engine.validate.api.validate_files` 提供；
- 本模块仅负责：运行期开关、按文件缓存、错误/警告聚合与便捷 API。
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Dict, List, Set, Tuple

from engine.configs.settings import settings


class NodeGraphValidationError(Exception):
    """节点图代码规范错误"""


class NodeGraphValidator:
    """节点图验证器：基于文件粒度委托引擎进行校验。"""

    def __init__(self, strict: bool = True):
        self.strict = strict
        self.errors: List[str] = []
        self.warnings: List[str] = []
        # 已完成校验的文件绝对路径集合：同一节点图文件只在当前进程中校验一次
        self.validated_files: Set[str] = set()

    def validate_class(self, node_graph_class) -> None:
        """基于所属文件调用引擎校验并在严格模式下抛错。"""
        # 运行时节点图校验可通过全局设置开关控制（默认关闭，仅在调试模式下启用）
        if not getattr(settings, "RUNTIME_NODE_GRAPH_VALIDATION_ENABLED", False):
            return

        source_file = inspect.getsourcefile(node_graph_class)
        if not isinstance(source_file, str) or len(source_file) == 0:
            return

        absolute_target = str(Path(source_file).resolve())
        # 同一文件在当前进程中仅校验一次，避免重复解析与规则执行
        if absolute_target in self.validated_files:
            return

        # 每次针对单个文件校验前清空累计问题列表
        self.errors = []
        self.warnings = []

        issues = _collect_issues_for_files([Path(source_file)])
        file_issues = issues.get(absolute_target, {"errors": [], "warnings": []})
        self.errors = file_issues["errors"]
        self.warnings = file_issues["warnings"]
        self.validated_files.add(absolute_target)

        if self.errors and self.strict:
            raise NodeGraphValidationError("\n".join(f"[X] {message}" for message in self.errors))


_global_validator = NodeGraphValidator(strict=True)


def validate_node_graph(node_graph_class):
    """验证节点图类（装饰器或直接调用）

    用法1（装饰器）：
    ```python
    @validate_node_graph
    class 我的节点图:
        ...
    ```

    用法2（直接调用）：
    ```python
    class 我的节点图:
        ...

    validate_node_graph(我的节点图)
    ```

    Args:
        node_graph_class: 节点图类

    Returns:
        原始类（用于装饰器）

    Raises:
        NodeGraphValidationError: 如果发现规范错误
    """
    _global_validator.validate_class(node_graph_class)
    return node_graph_class


def validate_file(file_path: Path) -> Tuple[bool, List[str], List[str]]:
    """验证单个节点图文件。

    Args:
        file_path: 节点图文件路径

    Returns:
        (是否通过, 错误列表, 警告列表)
    """
    absolute_target = str(file_path.resolve())
    issues = _collect_issues_for_files([file_path])
    file_issues = issues.get(absolute_target, {"errors": [], "warnings": []})
    errors = file_issues["errors"]
    warnings = file_issues["warnings"]
    return (len(errors) == 0), errors, warnings


_DEFAULT_FALLBACK_ROOT = Path(__file__).resolve().parents[2]


def _looks_like_workspace_root(candidate: Path) -> bool:
    """判断 candidate 是否像是“仓库工作区根目录”。

    约定（本仓库）：
    - 根目录下存在 `constraints.txt`
    - 根目录下存在 `engine/` 目录
    """

    if not isinstance(candidate, Path):
        return False
    return (candidate / "constraints.txt").is_file() and (candidate / "engine").is_dir()


def _infer_workspace_root_for_validate_file(target_files: List[Path]) -> Path:
    """为 validate_file 的“直接运行节点图脚本”场景推断 workspace_root。

    优先从被校验文件路径向上寻找仓库根目录；找不到时再从当前模块路径向上寻找；
    最终兜底为引擎子目录（保持旧行为，确保最少不崩）。
    """

    search_roots: List[Path] = []
    for file_path in target_files:
        if isinstance(file_path, Path):
            search_roots.append(file_path.resolve())
    search_roots.append(Path(__file__).resolve())

    for start in search_roots:
        cursor = start if start.is_dir() else start.parent
        for candidate in (cursor, *cursor.parents):
            if _looks_like_workspace_root(candidate):
                return candidate

    return _DEFAULT_FALLBACK_ROOT


def _collect_issues_for_files(target_files: List[Path]) -> Dict[str, Dict[str, List[str]]]:
    """运行底层验证并聚合成“文件 → (错误/警告列表)”的映射。"""
    resolved_target_files: List[Path] = [path.resolve() for path in target_files]
    absolute_targets = {str(path) for path in resolved_target_files}
    issues: Dict[str, Dict[str, List[str]]] = {
        target: {"errors": [], "warnings": []} for target in absolute_targets
    }
    if not absolute_targets:
        return issues

    # 兼容“直接运行节点图文件”的自检场景：
    # 节点图校验会触发布局计算，而布局层需要从 settings 读取 workspace_root。
    # CLI/GUI 启动入口会提前调用 settings.set_config_path(workspace_root)，但直接 python xxx.py 时不会。
    # 这里会尽量从被校验文件向上推断仓库根目录，并在必要时注入到 settings。
    current_workspace = getattr(settings.__class__, "_workspace_root", None)
    workspace_root = current_workspace if isinstance(current_workspace, Path) else None
    if workspace_root is None or (not _looks_like_workspace_root(workspace_root)):
        workspace_root = _infer_workspace_root_for_validate_file(resolved_target_files)
        settings.set_config_path(workspace_root)

    from engine.validate.api import validate_files

    report = validate_files(resolved_target_files, workspace_root, strict_entity_wire_only=False)
    for issue in report.issues:
        issue_file = issue.file or ""
        if issue_file in issues:
            bucket = issues[issue_file]
            if issue.level == "error":
                bucket["errors"].append(issue.message)
            elif issue.level == "warning":
                bucket["warnings"].append(issue.message)
    return issues


