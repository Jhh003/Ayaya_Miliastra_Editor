from __future__ import annotations

from pathlib import Path

from PyQt6 import QtWidgets

from tools import smoke_test_ui_libraries as ui_smoke


_qt_app = QtWidgets.QApplication.instance()
if _qt_app is None:
    _qt_app = QtWidgets.QApplication([])


def test_ui_library_pages_smoke_skip_ocr() -> None:
    """
    冒烟级回归：资源库关键页面能被构造并完成一次基础刷新/筛选。

    说明：
    - 本测试不预热 OCR（避免依赖 onnxruntime 环境），仅覆盖 UI 组件构造与数据刷新链路；
    - 逻辑复用 `tools.smoke_test_ui_libraries` 的实现，确保工具入口与 pytest 回归同源。
    """
    workspace_root = Path(__file__).resolve().parents[2]

    resource_manager, package_index_manager, package_views = ui_smoke._build_package_view_candidates(
        workspace_root
    )

    ui_smoke._run_template_library_smoke(resource_manager, package_views)
    ui_smoke._run_entity_placement_smoke(resource_manager, package_views)
    ui_smoke._run_graph_library_smoke(resource_manager, package_index_manager)
    ui_smoke._run_package_library_smoke(resource_manager, package_index_manager)

    # 清理本测试创建的顶层 Widget，避免影响同进程的后续 UI 测试。
    for top_level_widget in list(QtWidgets.QApplication.topLevelWidgets()):
        top_level_widget.close()


