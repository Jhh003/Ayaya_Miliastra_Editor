# -*- coding: utf-8 -*-
"""
自动化步骤编排管线模块集合（拆分自 editor_exec_steps）。

说明：本包只承载“计划/预热/同步/缓存策略/回放记录”等横切关注点，
不在此处实现具体的节点创建/连线/配置业务逻辑。
"""

from .step_plans import StepExecutionPlan, resolve_step_plan
from .recognition_prewarm import prepare_for_connect_if_needed
from .viewport_sync import sync_view_if_needed
from .cache_policy import (
    EXECUTE_STEP_LOG_KEY,
    invalidate_before_step,
    invalidate_after_success,
)
from .replay_recorder import (
    AutomationReplayRecorder,
    get_or_create_replay_recorder,
    should_record_step_io,
)


