import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QProgressDialog

from src.core.i18n import g_message
from src.core.settings import g_settings


class ScanArchiveProgressDialog(QProgressDialog):

    progress_signal = Signal()

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.setWindowTitle(g_message.UI_20260103_120010)
        self.setCancelButtonText(g_message.UI_20251231_180011)
        self.setMinimum(0)
        self.setValue(0)
        self.setMinimumDuration(0)

        self.progress_signal.connect(self._update_progress)

    def scan(self, rar_files: list[str]) -> bool:
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


def scan_archive() -> bool:
    """ 
    :return: 是否扫描成功
    """
    rar_files = list(map(os.path.abspath, Path(g_settings.resource_directory).rglob("*.rar")))
    if not rar_files:
        return True

    scan_progress_dialog = ScanArchiveProgressDialog()
    return scan_progress_dialog.scan(rar_files)

