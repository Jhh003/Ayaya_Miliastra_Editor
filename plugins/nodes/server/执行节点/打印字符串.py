from __future__ import annotations

from engine.nodes.node_spec import node_spec
from plugins.nodes.shared.server_执行节点_impl_helpers import *
from engine.utils.logging.logger import log_print


@node_spec(
    name="打印字符串",
    category="执行节点",
    inputs=[("流程入", "流程"), ("字符串", "字符串")],
    outputs=[("流程出", "流程")],
    aliases=["S打印字符串"],
    description="在日志中输出一条字符串，一般用于逻辑检测和调试。无论是否勾选该节点图，逻辑成功运行时该字符串都会打印。",
    doc_reference="服务器节点/执行节点/执行节点.md",
)
def 打印字符串(game, 字符串):
    """在日志中输出一条字符串，一般用于逻辑检测和调试。"""
    log_print("{}", 字符串)


