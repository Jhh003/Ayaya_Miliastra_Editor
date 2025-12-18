from __future__ import annotations

"""
导入门面：GraphView 的实现位于 `app.ui.graph.graph_view_impl`。

保留本文件仅用于：
- 旧的“按文件路径加载”（如历史脚本/工具）不至于复制出第二份 GraphView 类对象；
- 未来若有人错误地使用 `spec_from_file_location` 加载本文件，也会稳定复用 `graph_view_impl`。

标准导入路径：
- `from app.ui.graph.graph_view import GraphView`（推荐，来自包导出）
- 或 `from app.ui.graph.graph_view_impl import GraphView`
"""

from app.ui.graph.graph_view_impl import GraphView

__all__ = ["GraphView"]
