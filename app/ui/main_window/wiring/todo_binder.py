from __future__ import annotations

from typing import Any, Callable, Dict

from app.models import UiNavigationRequest


def bind_todo_page(
    *,
    todo_widget: Any,
    nav_coordinator: Any,
    on_todo_checked: Callable[[str, bool], None],
) -> None:
    """绑定任务清单页面对外信号。

    约定：
    - todo_widget 提供 `todo_checked`, `jump_to_task` 信号
    - Todo 预览的“跳转到图元素”信号来自全局唯一的 `main_window.app_state.graph_view.jump_to_graph_element`
    - nav_coordinator 提供 `handle_request(UiNavigationRequest)` 方法
    """

    todo_widget.todo_checked.connect(on_todo_checked)

    def _on_todo_jump_to_task(detail_info: Dict[str, object]) -> None:
        request = UiNavigationRequest.for_todo_task(detail_info, origin="todo")
        nav_coordinator.handle_request(request)

    def _on_todo_preview_jump(jump_info: Dict[str, object]) -> None:
        # GraphView 是全局共享的：在非 TODO 模式下也可能发出 jump_to_graph_element（例如双击复合节点）。
        # 这里必须按当前模式做门禁，避免编辑器中的双击被 Todo 跳转逻辑误处理。
        main_window = getattr(todo_widget, "main_window", None)
        if main_window is not None and hasattr(main_window, "central_stack"):
            from app.models.view_modes import ViewMode

            current_mode = ViewMode.from_index(main_window.central_stack.currentIndex())
            if current_mode is not ViewMode.TODO:
                return

        request = UiNavigationRequest.for_todo_preview_jump(jump_info, origin="todo_preview")
        if request is None:
            return
        nav_coordinator.handle_request(request)

    todo_widget.jump_to_task.connect(_on_todo_jump_to_task)
    main_window = getattr(todo_widget, "main_window", None)
    app_state = getattr(main_window, "app_state", None) if main_window is not None else None
    graph_view = getattr(app_state, "graph_view", None) if app_state is not None else None
    if graph_view is not None and hasattr(graph_view, "jump_to_graph_element"):
        graph_view.jump_to_graph_element.connect(_on_todo_preview_jump)


