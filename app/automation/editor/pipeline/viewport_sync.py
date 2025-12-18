# -*- coding: utf-8 -*-
"""
视口同步（单步模式）。

职责：当视口 token 发生变化时，同步一批可见节点的坐标漂移缓存，避免后续步骤使用过期位置。
"""

from engine.graph.models.graph_model import GraphModel

from .step_plans import StepExecutionPlan


def sync_view_if_needed(
    executor,
    graph_model: GraphModel,
    step_plan: StepExecutionPlan,
    log_callback=None,
) -> None:
    # fast_chain_mode=True 时跳过（连续链路由外层保证视口与识别一致）
    if bool(getattr(executor, "fast_chain_mode", False)):
        return
    if not bool(step_plan.requires_view_sync):
        return

    if executor.should_sync_visible_nodes_positions():
        synced_count = executor.sync_visible_nodes_positions(
            graph_model,
            threshold_px=60.0,
            log_callback=log_callback,
        )
        executor.mark_visible_nodes_positions_synced()
        if synced_count > 0:
            executor.log(
                f"· 单步：同步可见节点坐标 {synced_count} 个，避免使用过期位置",
                log_callback,
            )
        else:
            executor.log("· 单步：重新确认视口，无可更新坐标", log_callback)
        return

    executor.log("· 单步：视口未变化，跳过可见节点同步", log_callback)


