"""Utility helpers for drawing scene backgrounds."""

import math

from PyQt6 import QtGui

from app.ui.graph.graph_palette import GraphPalette


def draw_grid_background(painter, rect, grid_size: int = 50) -> None:
    """Render a dark grid background used by QGraphicsScene."""
    painter.fillRect(rect, QtGui.QColor(GraphPalette.CANVAS_BG))

    # 使用 floor 对齐网格起点，确保在负坐标/缩放/平移下网格不会因为“向 0 截断”的取整行为而产生跳变。
    left = math.floor(float(rect.left()) / grid_size) * grid_size
    top = math.floor(float(rect.top()) / grid_size) * grid_size

    light_grid_pen = QtGui.QPen(QtGui.QColor(GraphPalette.GRID_LIGHT), 1)
    painter.setPen(light_grid_pen)

    x = left
    while x < rect.right():
        painter.drawLine(int(x), int(rect.top()), int(x), int(rect.bottom()))
        x += grid_size

    y = top
    while y < rect.bottom():
        painter.drawLine(int(rect.left()), int(y), int(rect.right()), int(y))
        y += grid_size

    thick_grid_pen = QtGui.QPen(QtGui.QColor(GraphPalette.GRID_BOLD), 2)
    painter.setPen(thick_grid_pen)

    x = left
    while x < rect.right():
        if int(x) % (grid_size * 5) == 0:
            painter.drawLine(int(x), int(rect.top()), int(x), int(rect.bottom()))
        x += grid_size

    y = top
    while y < rect.bottom():
        if int(y) % (grid_size * 5) == 0:
            painter.drawLine(int(rect.left()), int(y), int(rect.right()), int(y))
        y += grid_size


