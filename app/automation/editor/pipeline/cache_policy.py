# -*- coding: utf-8 -*-
"""
缓存失效策略（步骤前后）。

职责：
- 步骤前：根据步骤类型失效连续连线上下文等“可复用状态”；
- 步骤成功后：按计划失效视觉缓存/场景快照，确保后续识别不会误用旧画面。
"""

from app.automation.vision import invalidate_cache

from ..automation_step_types import GRAPH_STEP_CONNECT_MERGED
from .step_plans import StepExecutionPlan


EXECUTE_STEP_LOG_KEY = "app.automation.editor.EditorExecutor.execute_step"


def invalidate_before_step(executor, step_type: str) -> None:
    # 合并连线允许跨边复用链上下文（node_snapshots 等），因此不在此处失效
    if str(step_type or "") != GRAPH_STEP_CONNECT_MERGED:
        executor.invalidate_connect_chain_context("step type changed")


def invalidate_after_success(executor, step_type: str, step_plan: StepExecutionPlan) -> None:
    if bool(step_plan.invalidate_cache_on_success):
        invalidate_cache()

    if bool(getattr(step_plan, "mutates_layout", False)):
        invalidate_scene = getattr(executor, "invalidate_scene_snapshot", None)
        if callable(invalidate_scene):
            invalidate_scene(f"step:{step_type}")


