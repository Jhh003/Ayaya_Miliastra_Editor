from __future__ import annotations

from pathlib import Path

from engine.validate.api import validate_files


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _write_graph_code(tmp_dir: Path, filename: str, source: str) -> Path:
    target = tmp_dir / filename
    target.write_text(source, encoding="utf-8")
    return target


def test_local_variable_without_initial_value_in_graph_reports_issue(tmp_path: Path) -> None:
    """Graph Code 中显式使用【获取局部变量】但未提供『初始值』时，应报错。"""
    graph_code = '''
""" 
graph_id: graph_local_var_missing_initial
graph_name: 局部变量缺少初始值_图
graph_type: server
"""

from __future__ import annotations

from _prelude import *


class 局部变量缺少初始值_图:
    def __init__(self, game, owner_entity):
        self.game = game
        self.owner_entity = owner_entity

    def on_实体创建时(self, 事件源实体, 事件源GUID):
        局部句柄, 当前值 = 获取局部变量(self.game)
        设置局部变量(self.game, 局部变量=局部句柄, 值=1)
'''
    workspace = _workspace_root()
    graph_path = _write_graph_code(tmp_path, "graph_local_var_missing_initial.py", graph_code)

    report = validate_files(
        [graph_path],
        workspace,
        strict_entity_wire_only=False,
        use_cache=False,
    )
    issues = [issue for issue in report.issues if issue.code == "CODE_LOCAL_VAR_INITIAL_REQUIRED"]

    assert issues, "显式使用【获取局部变量】但未提供『初始值』时，应报局部变量初始值缺失错误"


def test_local_variable_with_initial_value_in_graph_is_ok(tmp_path: Path) -> None:
    """Graph Code 中【获取局部变量】提供了『初始值』时，不应报本规则错误。"""
    graph_code = '''
""" 
graph_id: graph_local_var_with_initial
graph_name: 局部变量有初始值_图
graph_type: server
"""

from __future__ import annotations

from _prelude import *


class 局部变量有初始值_图:
    def __init__(self, game, owner_entity):
        self.game = game
        self.owner_entity = owner_entity

    def on_实体创建时(self, 事件源实体, 事件源GUID):
        局部句柄, 当前值 = 获取局部变量(self.game, 初始值=0)
        设置局部变量(self.game, 局部变量=局部句柄, 值=1)
'''
    workspace = _workspace_root()
    graph_path = _write_graph_code(tmp_path, "graph_local_var_with_initial.py", graph_code)

    report = validate_files(
        [graph_path],
        workspace,
        strict_entity_wire_only=False,
        use_cache=False,
    )
    issues = [issue for issue in report.issues if issue.code == "CODE_LOCAL_VAR_INITIAL_REQUIRED"]

    assert not issues, "【获取局部变量】已提供『初始值』时，不应触发局部变量初始值缺失错误"


def test_local_variable_without_initial_value_in_composite_reports_issue(tmp_path: Path) -> None:
    """复合节点类格式中使用【获取局部变量】但未提供『初始值』时，应报错。"""
    composite_code = '''
"""
composite_id: composite_local_var_missing_initial
composite_name: 复合_局部变量缺少初始值
description: 用于验证复合节点中的局部变量初始值校验规则
scope: server
"""

from runtime.engine.graph_prelude_server import *
from engine.nodes.composite_spec import composite_class, data_method


@composite_class
class 复合_局部变量缺少初始值:
    def __init__(self, game, owner_entity):
        self.game = game
        self.owner_entity = owner_entity

    @data_method(
        inputs=[],
        outputs=[("结果", "整数")],
    )
    def 计算(self):
        局部句柄, 当前值 = 获取局部变量(self.game)
        设置局部变量(self.game, 局部变量=局部句柄, 值=1)
        return 当前值
'''
    workspace = _workspace_root()
    composite_path = _write_graph_code(
        tmp_path,
        "composite_local_var_missing_initial.py",
        composite_code,
    )

    report = validate_files(
        [composite_path],
        workspace,
        strict_entity_wire_only=False,
        use_cache=False,
    )
    issues = [issue for issue in report.issues if issue.code == "CODE_LOCAL_VAR_INITIAL_REQUIRED"]

    assert issues, "复合节点中使用【获取局部变量】但未提供『初始值』时，应报局部变量初始值缺失错误"


