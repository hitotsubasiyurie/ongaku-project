import sys
from queue import Empty
from multiprocessing import Queue, Process, Pipe
from typing import Callable, TypeVar, Optional, Any

from PySide6.QtCore import QEventLoop, QTimer, Qt
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPlainTextEdit, 
    QLineEdit, QPushButton, QHBoxLayout
)

_T = TypeVar("_T")


class ProcessIOStream:
    """子进程的 IO 流"""

    def __init__(self) -> None:
        self.stdin_queue = Queue()
        self.stdout_queue = Queue()

    def write(self, s: str) -> None:
        s and self.stdout_queue.put(s)

    def readline(self) -> str:
        # 阻塞取值
        return self.stdin_queue.get(block=True)


class Terminal(QWidget):

    def setup_ui(self) -> None:
        """初始化 UI"""
        self.text_edit = QPlainTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.line_edit = QLineEdit(self)
        self.line_edit.setPlaceholderText("Enter...")
        self.button = QPushButton("Send", self)

        top = QVBoxLayout(self)
        top.addWidget(self.text_edit, 1)
        row = QHBoxLayout()
        row.addWidget(self.line_edit, 1)
        row.addWidget(self.button)
        top.addLayout(row)

    def setup_event(self) -> None:
        """初始化 事件"""
        self.button.clicked.connect(self._on_text_input)
        self.line_edit.returnPressed.connect(self._on_text_input)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Terminal")

        self.setup_ui()

        self.iostream = ProcessIOStream()

        self._process: Process = None
        self._poll_timer = QTimer(self, timeout=self._poll)

    def execute(self, func: Callable[..., _T], *args, **kwargs) -> _T:
        """同步阻塞调用，但不卡死 UI"""
        self.text_edit.clear()

        loop = QEventLoop()
        parent_conn, child_conn = Pipe(duplex=True)

        def _execute(func, args, kwargs) -> None:
            try:
                result = func(*args, **kwargs)
                child_conn.send(result)
            except Exception as e:
                child_conn.send(e)

        self._process = Process(target=_execute, args=(func, args, kwargs), daemon=True)
        self._process.start()

        self._poll_timer.start(50)

        self.show()
        loop.exec()

        # 清理状态
        self._process.is_alive() and self._process.terminate()
        self._process = None
        self._poll_timer.stop()

        if not parent_conn.poll():
            return
        result = parent_conn.recv()
        if isinstance(result, Exception):
            raise result
        return result

    # 重写方法

    def showEvent(self, event) -> None:
        self.text_edit.clear()
        self.line_edit.clear()
        self.line_edit.setFocus()
        super().showEvent(event)

    # 内部方法

    def _poll(self) -> None:
        # 清空 stdout 队列
        try:
            while True:
                s = self.iostream.stdout_queue.get_nowait()
                self.text_edit.appendPlainText(s)
        except Empty:
            pass
        if not self._process or not self._process.is_alive():
            self.close()

    def _on_text_input(self) -> None:
        s = self.line_edit.text()
        if s:
            self.text_edit.appendPlainText(f"> {s}")
            self.iostream.stdin_queue.put(s)
            self.line_edit.clear()


# --- 使用示例 ---
def business_logic(stream: ProcessIOStream):
    stream.write("System: 请输入您的指令...")
    cmd = stream.readline()
    stream.write(f"System: 正在执行 {cmd}...")
    import time
    time.sleep(20)
    return f"Success: {cmd}"

if __name__ == "__main__":
    app = QApplication(sys.argv)
    term = Terminal()
    
    # 模拟在主程序中调用
    term.execute(business_logic, term.iostream)
    
    sys.exit(app.exec())
