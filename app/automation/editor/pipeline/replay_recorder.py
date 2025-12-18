# -*- coding: utf-8 -*-
"""
关键步骤回放记录（输入/输出落盘）。

目标：
- 将“关键步骤”的输入（todo_item、step_type、关键运行态字段）与输出（success/失败原因）落盘；
- 可选落盘步骤前后截图，辅助回归定位与离线复现。
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from app.automation import capture as editor_capture
from app.runtime.services import get_shared_json_cache_service
from engine.configs.settings import settings

from .step_plans import StepExecutionPlan


def _sanitize_for_json(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        sanitized: Dict[str, Any] = {}
        for key, item in value.items():
            sanitized[str(key)] = _sanitize_for_json(item)
        return sanitized
    if isinstance(value, (list, tuple)):
        return [_sanitize_for_json(item) for item in value]
    return str(value)


def _get_step_index(executor) -> int:
    step_index_value = getattr(executor, "_current_step_index", -1)
    if isinstance(step_index_value, bool):
        return -1
    if isinstance(step_index_value, int):
        return int(step_index_value)
    if isinstance(step_index_value, float):
        return int(step_index_value)
    step_index_text = str(step_index_value).strip()
    if not step_index_text:
        return -1
    if step_index_text.startswith("-") and step_index_text[1:].isdigit():
        return -int(step_index_text[1:])
    if step_index_text.isdigit():
        return int(step_index_text)
    return -1


def _is_recording_enabled() -> bool:
    return bool(getattr(settings, "REAL_EXEC_REPLAY_RECORDING_ENABLED", False))


def _is_screenshot_enabled() -> bool:
    return bool(getattr(settings, "REAL_EXEC_REPLAY_CAPTURE_SCREENSHOTS", False))


def should_record_step_io(step_type: str, step_plan: Optional[StepExecutionPlan]) -> bool:
    if not _is_recording_enabled():
        return False
    if bool(getattr(settings, "REAL_EXEC_REPLAY_RECORD_ALL_STEPS", False)):
        return True
    if step_plan is None:
        return False
    return bool(getattr(step_plan, "record_replay_io", False))


@dataclass
class AutomationReplayRecorder:
    workspace_root: Path
    run_id: str

    @property
    def cache_service(self):
        return get_shared_json_cache_service(self.workspace_root)

    @property
    def output_dir(self) -> Path:
        return self.cache_service.resolve_cache_path(f"automation_replay/{self.run_id}")

    @property
    def steps_jsonl_path(self) -> Path:
        return self.output_dir / "steps.jsonl"

    def record_event(
        self,
        *,
        executor,
        stage: str,
        step_type: str,
        todo_item: Dict[str, Any],
        step_plan: Optional[StepExecutionPlan],
        success: Optional[bool],
        reason: str = "",
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        view_state_token_value = getattr(executor, "get_view_state_token", None)
        view_state_token = view_state_token_value() if callable(view_state_token_value) else -1

        payload: Dict[str, Any] = {
            "ts": float(time.time()),
            "stage": str(stage),
            "step_index": _get_step_index(executor),
            "step_type": str(step_type or ""),
            "todo_item": _sanitize_for_json(todo_item),
            "success": success,
            "reason": str(reason or ""),
            "view_state_token": int(view_state_token),
            "scale_ratio": _sanitize_for_json(getattr(executor, "scale_ratio", None)),
            "origin_node_pos": _sanitize_for_json(getattr(executor, "origin_node_pos", None)),
            "fast_chain_mode": bool(getattr(executor, "fast_chain_mode", False)),
        }
        if step_plan is not None:
            payload["plan"] = {
                "requires_connect_prepare": bool(step_plan.requires_connect_prepare),
                "requires_view_sync": bool(step_plan.requires_view_sync),
                "invalidate_cache_on_success": bool(step_plan.invalidate_cache_on_success),
                "mutates_layout": bool(getattr(step_plan, "mutates_layout", False)),
                "record_replay_io": bool(getattr(step_plan, "record_replay_io", False)),
            }
        if extra:
            payload["extra"] = _sanitize_for_json(extra)

        self.cache_service.append_jsonl(
            f"automation_replay/{self.run_id}/steps.jsonl",
            payload,
            ensure_ascii=False,
            sort_keys=False,
        )

    def record_screenshot(
        self,
        *,
        executor,
        stage: str,
        step_type: str,
    ) -> Optional[str]:
        if not _is_screenshot_enabled():
            return None

        screenshot = editor_capture.capture_window_strict(executor.window_title)
        if screenshot is None:
            screenshot = editor_capture.capture_window(executor.window_title)
        if screenshot is None:
            return None

        self.output_dir.mkdir(parents=True, exist_ok=True)
        step_index = _get_step_index(executor)
        safe_step_type = str(step_type or "").replace("/", "_").replace("\\", "_").replace(":", "_")
        filename = f"{step_index:04d}_{safe_step_type}_{stage}.png"
        output_path = self.cache_service.resolve_cache_path(f"automation_replay/{self.run_id}/{filename}")
        screenshot.save(output_path)
        return str(output_path)


def get_or_create_replay_recorder(executor) -> Optional[AutomationReplayRecorder]:
    if not _is_recording_enabled():
        return None

    existing = getattr(executor, "_automation_replay_recorder", None)
    if isinstance(existing, AutomationReplayRecorder):
        return existing

    workspace_value = getattr(executor, "workspace_path", None)
    workspace_root = Path(workspace_value) if workspace_value is not None else Path(".")
    run_id = time.strftime("%Y%m%d_%H%M%S")
    recorder = AutomationReplayRecorder(workspace_root=workspace_root, run_id=run_id)
    if hasattr(executor, "__dict__"):
        setattr(executor, "_automation_replay_recorder", recorder)
    return recorder


