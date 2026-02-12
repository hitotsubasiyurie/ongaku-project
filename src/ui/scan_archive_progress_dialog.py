import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from PySide6.QtWidgets import QWidget, QProgressDialog
from PySide6.QtCore import Signal

from src.core.i18n import MESSAGE
from src.core.settings import settings
from src.core.kanban import FunctionCallCache


class ScanArchiveProgressDialog(QProgressDialog):

    progress_signal = Signal()

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.setWindowTitle(MESSAGE.UI_20260103_120010)
        self.setCancelButtonText(MESSAGE.UI_20251231_180011)
        self.setMinimum(0)
        self.setValue(0)
        self.setMinimumDuration(0)

        self.progress_signal.connect(self._update_progress)

    def scan_archive(self) -> bool:
        rar_files = list(map(os.path.abspath, Path(settings.resource_directory).rglob("*.rar")))
        if not rar_files:
            self.close()
            return True
        
        self.setMaximum(len(rar_files))

        # 默认 max_workers = cpu_count + 4
        executor = ThreadPoolExecutor()
        [executor.submit(self._work, f) for f in rar_files]

        self.show()
        # 等待完成或取消
        completed = self.exec() == self.DialogCode.Accepted

        executor.shutdown(wait=True, cancel_futures=(not completed))
        return completed

    def _work(self, f: str) -> None:
        FunctionCallCache.rar_list(f)
        FunctionCallCache.rar_stats(f)
        self.progress_signal.emit()

    def _update_progress(self) -> None:
        v = self.value() + 1
        self.setValue(v)
        # 完成
        if v >= self.maximum():
            self.accept()
