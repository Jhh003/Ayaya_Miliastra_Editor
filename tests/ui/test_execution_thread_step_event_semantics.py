from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from PyQt6 import QtWidgets

from app.ui.execution.thread import ExecutionThread
from engine.graph.models.graph_model import GraphModel


_app = QtWidgets.QApplication.instance()
if _app is None:
    _app = QtWidgets.QApplication([])


@dataclass
class DummyAnchorInfo:
    skip_first_todo_id: str | None = None


class DummyTodoStep:
    def __init__(self, *, todo_id: str, title: str, detail_info: dict) -> None:
        self.todo_id = todo_id
        self.title = title
        self.detail_info = detail_info


class DummyMonitor:
    def __init__(self) -> None:
        self.logs: List[str] = []
        self.status_updates: List[str] = []

    def log(self, message: str) -> None:
        self.logs.append(str(message))

    def update_status(self, status: str) -> None:
        self.status_updates.append(str(status))

    def wait_if_paused(self) -> None:
        return

    def is_execution_allowed(self) -> bool:
        return True

    def update_visual(self, _image, _overlays) -> None:
        return


class DummySkipDecision:
    def __init__(self, should_skip: bool = False, reason: str = "") -> None:
        self.should_skip = should_skip
        self.reason = reason


class DummySkipChecker:
    def check_should_skip(
        self,
        _step_info: dict,
        _skip_first_create_after_calibration: bool,
        _skip_first_create_todo_id: str | None,
        _step_todo_id: str,
    ) -> DummySkipDecision:
        return DummySkipDecision(should_skip=False)

    def ensure_endpoints_visible(self, *_args, **_kwargs) -> None:
        return


class DummyRetryResult:
    def __init__(self, success: bool, did_retry: bool) -> None:
        self.success = bool(success)
        self.did_retry = bool(did_retry)


class DummyRetryHandler:
    def __init__(self, results: List[DummyRetryResult]) -> None:
        self._results = list(results)

    def try_retry_with_anchor_fallback(self, _step_info: dict, _step_todo_id: str) -> DummyRetryResult:
        if self._results:
            return self._results.pop(0)
        return DummyRetryResult(success=False, did_retry=False)

    def update_anchor_after_success(self, _step_info: dict) -> None:
        return


class DummySummaryBuilder:
    def build_summary(self, step_info: dict) -> str:
        step_type = str(step_info.get("type", ""))
        return f"summary(type={step_type})"


class DummyExecutor:
    pass


def _run_steps_directly(thread: ExecutionThread, steps: list) -> None:
    # 避免触发真实执行器逻辑：用假策略覆盖关键依赖。
    thread.summary_builder = DummySummaryBuilder()
    thread.skip_checker = DummySkipChecker()
    thread._update_fast_chain_scope = lambda _step_type: None
    thread._execute_steps_loop(DummyAnchorInfo(skip_first_todo_id=None), skip_first_create_after_calibration=False)


def test_execution_thread_emits_step_completed_once_when_retry_succeeds() -> None:
    graph_model = GraphModel(graph_id="g1")
    monitor = DummyMonitor()
    executor = DummyExecutor()

    step = DummyTodoStep(
        todo_id="t1",
        title="create-node",
        detail_info={"type": "graph_create_node", "node_id": "n1"},
    )
    thread = ExecutionThread(executor, graph_model, [step], monitor)

    thread.retry_handler = DummyRetryHandler([DummyRetryResult(success=True, did_retry=True)])
    thread._execute_single_step = lambda _step_info: (False, "fail-first")
    thread._get_max_step_retry_limit = lambda: 3

    started_events: List[str] = []
    completed_events: List[Tuple[str, bool]] = []
    skipped_events: List[Tuple[str, str]] = []

    thread.step_will_start.connect(lambda todo_id: started_events.append(str(todo_id)))
    thread.step_completed.connect(lambda todo_id, success: completed_events.append((str(todo_id), bool(success))))
    thread.step_skipped.connect(lambda todo_id, reason: skipped_events.append((str(todo_id), str(reason))))

    _run_steps_directly(thread, [step])

    assert started_events == ["t1"]
    assert skipped_events == []
    assert completed_events == [("t1", True)]


def test_execution_thread_skips_non_create_step_after_failed_retries_without_step_completed() -> None:
    graph_model = GraphModel(graph_id="g1")
    monitor = DummyMonitor()
    executor = DummyExecutor()

    step = DummyTodoStep(
        todo_id="t1",
        title="connect",
        detail_info={"type": "graph_connect", "src_node": "a", "dst_node": "b"},
    )
    thread = ExecutionThread(executor, graph_model, [step], monitor)

    thread.retry_handler = DummyRetryHandler(
        [
            DummyRetryResult(success=False, did_retry=True),
            DummyRetryResult(success=False, did_retry=True),
        ]
    )
    thread._execute_single_step = lambda _step_info: (False, "connect-failed")
    thread._get_max_step_retry_limit = lambda: 2

    started_events: List[str] = []
    completed_events: List[Tuple[str, bool]] = []
    skipped_events: List[Tuple[str, str]] = []

    thread.step_will_start.connect(lambda todo_id: started_events.append(str(todo_id)))
    thread.step_completed.connect(lambda todo_id, success: completed_events.append((str(todo_id), bool(success))))
    thread.step_skipped.connect(lambda todo_id, reason: skipped_events.append((str(todo_id), str(reason))))

    _run_steps_directly(thread, [step])

    assert started_events == ["t1"]
    assert completed_events == []
    assert len(skipped_events) == 1
    assert skipped_events[0][0] == "t1"
    assert "connect-failed" in skipped_events[0][1]


def test_execution_thread_emits_step_completed_once_on_final_fatal_failure() -> None:
    graph_model = GraphModel(graph_id="g1")
    monitor = DummyMonitor()
    executor = DummyExecutor()

    step = DummyTodoStep(
        todo_id="t1",
        title="create-node",
        detail_info={"type": "graph_create_node", "node_id": "n1"},
    )
    thread = ExecutionThread(executor, graph_model, [step], monitor)

    thread.retry_handler = DummyRetryHandler(
        [
            DummyRetryResult(success=False, did_retry=True),
            DummyRetryResult(success=False, did_retry=True),
        ]
    )
    thread._execute_single_step = lambda _step_info: (False, "fatal-failed")
    thread._get_max_step_retry_limit = lambda: 2

    started_events: List[str] = []
    completed_events: List[Tuple[str, bool]] = []
    skipped_events: List[Tuple[str, str]] = []

    thread.step_will_start.connect(lambda todo_id: started_events.append(str(todo_id)))
    thread.step_completed.connect(lambda todo_id, success: completed_events.append((str(todo_id), bool(success))))
    thread.step_skipped.connect(lambda todo_id, reason: skipped_events.append((str(todo_id), str(reason))))

    _run_steps_directly(thread, [step])

    assert started_events == ["t1"]
    assert skipped_events == []
    assert completed_events == [("t1", False)]


