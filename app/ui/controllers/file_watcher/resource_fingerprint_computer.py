from __future__ import annotations

from PyQt6 import QtCore

from engine.resources.resource_manager import ResourceManager


class ResourceFingerprintComputer(QtCore.QObject):
    """后台线程：计算资源库指纹，避免主线程扫描文件系统导致 UI 卡顿。"""

    fingerprint_computed = QtCore.pyqtSignal(str)

    def __init__(self, resource_manager: ResourceManager) -> None:
        super().__init__()
        self._resource_manager = resource_manager

    @QtCore.pyqtSlot()
    def run(self) -> None:
        fingerprint_value = self._resource_manager.compute_resource_library_fingerprint()
        self.fingerprint_computed.emit(str(fingerprint_value or ""))


