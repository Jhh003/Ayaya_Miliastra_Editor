from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.models.edit_session_capabilities import EditSessionCapabilities


GraphSaveStatus = Literal["readonly", "saved", "unsaved", "saving"]


@dataclass(slots=True)
class GraphEditorSessionStateMachine:
    """节点图编辑会话状态机（不可分叉的单一真源）。

    约束目标：
    - `EditSessionCapabilities` 与 `save_status` 的推导在同一处完成；
    - controller/view/scene 不再分别维护 read_only/dirty/saving 等 bool；
    - 只读会话（can_persist=False）始终呈现 `save_status="readonly"`，避免 UI 误导。
    """

    capabilities: EditSessionCapabilities
    current_graph_id: str | None = None
    baseline_content_hash: str | None = None
    save_status: GraphSaveStatus = "readonly"

    def set_capabilities(self, capabilities: EditSessionCapabilities, *, current_content_hash: str | None) -> GraphSaveStatus:
        self.capabilities = capabilities

        if not self.capabilities.can_persist:
            self.save_status = "readonly"
            if current_content_hash is not None:
                self.baseline_content_hash = str(current_content_hash)
            return self.save_status

        if self.current_graph_id is None:
            self.save_status = "saved"
            return self.save_status

        if self.baseline_content_hash is None or current_content_hash is None:
            self.save_status = "unsaved"
            return self.save_status

        self.save_status = "saved" if str(current_content_hash) == str(self.baseline_content_hash) else "unsaved"
        return self.save_status

    def on_graph_loaded(self, *, graph_id: str, baseline_content_hash: str) -> GraphSaveStatus:
        self.current_graph_id = str(graph_id)
        self.baseline_content_hash = str(baseline_content_hash)
        self.save_status = "saved" if self.capabilities.can_persist else "readonly"
        return self.save_status

    def on_graph_closed(self) -> GraphSaveStatus:
        self.current_graph_id = None
        self.baseline_content_hash = None
        self.save_status = "readonly" if not self.capabilities.can_persist else "saved"
        return self.save_status

    def has_unsaved_changes(self, *, current_content_hash: str | None) -> bool:
        if not self.capabilities.can_persist:
            return False
        if self.current_graph_id is None:
            return False
        if self.baseline_content_hash is None or current_content_hash is None:
            return False
        return str(current_content_hash) != str(self.baseline_content_hash)

    def on_modified(self, *, current_content_hash: str) -> GraphSaveStatus:
        if not self.capabilities.can_persist:
            self.baseline_content_hash = str(current_content_hash)
            self.save_status = "readonly"
            return self.save_status

        if self.baseline_content_hash is not None and str(current_content_hash) == str(self.baseline_content_hash):
            self.save_status = "saved"
            return self.save_status

        self.save_status = "unsaved"
        return self.save_status

    def on_save_started(self) -> GraphSaveStatus:
        self.save_status = "saving" if self.capabilities.can_persist else "readonly"
        return self.save_status

    def on_save_succeeded(self, *, new_baseline_content_hash: str) -> GraphSaveStatus:
        self.baseline_content_hash = str(new_baseline_content_hash)
        self.save_status = "saved" if self.capabilities.can_persist else "readonly"
        return self.save_status

    def on_save_failed(self) -> GraphSaveStatus:
        self.save_status = "unsaved" if self.capabilities.can_persist else "readonly"
        return self.save_status


