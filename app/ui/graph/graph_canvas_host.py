from __future__ import annotations

from PyQt6 import QtWidgets


class GraphCanvasHost(QtWidgets.QWidget):
    """一个只负责“承载 GraphView”的轻量容器。

    目的：
    - 允许同一个 `GraphView` 在不同页面之间移动（re-parent），从而实现画布复用；
    - 避免把 `GraphView` 直接作为 QStackedWidget 页导致“一个 widget 只能有一个 parent”的限制。
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._attached_view: QtWidgets.QWidget | None = None

    def attach_view(self, view: QtWidgets.QWidget) -> None:
        """将 view 挂载到本容器（幂等）。"""
        if view is self._attached_view and view.parentWidget() is self:
            return

        # 若 view 之前在其它容器里，先从旧 layout 中移除（Qt re-parent 通常会处理，
        # 但显式 remove 可以避免旧 layout 保留悬挂引用）。
        previous_parent = view.parentWidget()
        if previous_parent is not None and previous_parent is not self:
            previous_layout = previous_parent.layout()
            if previous_layout is not None:
                previous_layout.removeWidget(view)
            if isinstance(previous_parent, GraphCanvasHost):
                previous_parent._attached_view = None

        view.setParent(self)
        self._layout.addWidget(view)
        view.show()
        self._attached_view = view

    def detach_view(self) -> QtWidgets.QWidget | None:
        """将当前挂载的 view 从本容器移除并返回。"""
        if self._attached_view is None:
            return None
        view = self._attached_view
        self._layout.removeWidget(view)
        view.setParent(None)
        self._attached_view = None
        return view


