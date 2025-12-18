"""主窗口的共享状态对象（AppState）。

目标：
- 将启动期的稳定依赖（workspace / 节点库 / ResourceManager / PackageIndexManager / GraphView）集中到明确对象中；
- 避免在主窗口上保留 `self.*` 的兼容别名，减少跨域逻辑对隐式约定的依赖。

约定：
- **动态的** GraphModel/GraphScene 由 `GraphEditorController` 管理（加载图时会重建模型与场景），
  因此 AppState 不持有 `graph_model/graph_scene`，以避免出现“陈旧副本”。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.configs.settings import settings
from engine.graph.models.graph_model import GraphModel
from engine.nodes.node_registry import get_node_registry
from engine.resources import (
    PackageIndexManager,
    ResourceManager,
    build_resource_index_context,
    init_workspace_settings,
)
from engine.utils.logging.logger import log_info
from app.codegen import ExecutableCodeGenerator
from app.ui.graph.graph_scene import GraphScene
from app.ui.graph.graph_view import GraphView


@dataclass(slots=True)
class MainWindowAppState:
    """主窗口启动期装配得到的稳定依赖集合（单一真源）。"""

    workspace_path: Path
    node_library: dict
    resource_manager: ResourceManager
    package_index_manager: PackageIndexManager
    graph_view: GraphView


def build_main_window_app_state(workspace_path: Path) -> MainWindowAppState:
    """构建主窗口 AppState：集中完成 settings / 节点库 / 资源索引 / 图编辑器基础对象装配。"""
    log_info("[BOOT][AppState] 开始构建 MainWindowAppState，workspace={}", workspace_path)

    # 1) 初始化全局设置
    init_workspace_settings(workspace_path)
    settings.load()
    log_info(
        "[BOOT][AppState] settings 加载完成（UI_THEME_MODE={}）",
        getattr(settings, "UI_THEME_MODE", "unknown"),
    )

    # 2) 加载节点定义（集中式注册表）
    registry = get_node_registry(workspace_path, include_composite=True)
    node_library = registry.get_library()
    log_info("[BOOT][AppState] 节点库加载完成，当前节点定义数量={}", len(node_library))

    # 3) 资源管理器与存档索引管理器
    graph_code_generator = ExecutableCodeGenerator(workspace_path, node_library)
    resource_manager, package_index_manager = build_resource_index_context(
        workspace_path,
        init_settings_first=False,
        graph_code_generator=graph_code_generator,
    )
    log_info("[BOOT][AppState] ResourceManager / PackageIndexManager 初始化完成")

    # 4) 节点图编辑器基础对象（空图）
    graph_model = GraphModel()
    graph_scene = GraphScene(graph_model, node_library=node_library)
    graph_view = GraphView(graph_scene)
    graph_view.node_library = node_library
    log_info("[BOOT][AppState] GraphModel/GraphScene/GraphView 初始化完成")

    return MainWindowAppState(
        workspace_path=workspace_path,
        node_library=node_library,
        resource_manager=resource_manager,
        package_index_manager=package_index_manager,
        graph_view=graph_view,
    )


