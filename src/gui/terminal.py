import sys
import threading
from collections import deque
from typing import Callable, TypeVar

from PySide6.QtCore import QObject, Signal, QEventLoop
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPlainTextEdit, QLineEdit, QPushButton,
                               QHBoxLayout, QApplication)

_T = TypeVar("T")


class IOStream(QObject):

    text_written = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        # 流是否处于可用状态
        self.opened = False
        self._condition = threading.Condition()
        self._buffer: deque[str] = deque()

    # 协议方法

    def write(self, s: str) -> None:
        with self._condition:
            if not self.opened:
                raise BrokenPipeError("IO stream is not opened.")
            # s 不为空时发出信号
            s and self.text_written.emit(s)

    def flush(self) -> None:
        pass

    def readline(self) -> str:
        with self._condition:
            # condition.wait() 必须放在 while 循环中
            while not self._buffer and self.opened:
                self._condition.wait()
            if not self.opened:
                raise BrokenPipeError("IO stream is not opened.")
            return self._buffer.popleft()

    # GUI 控制

    def push(self, line: str) -> None:
        with self._condition:
            if not self.opened:
                return
            self._buffer.append(line)
            self._condition.notify()

    def open(self) -> None:
        with self._condition:
            self.opened = True

    def close(self) -> None:
        with self._condition:
            self.opened = False
            self._condition.notify_all()


class Terminal(QWidget):

    def setup_ui(self) -> None:
        """初始化 UI"""
        self.text_edit = QPlainTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.line_edit = QLineEdit(self)
        self.line_edit.setPlaceholderText("Enter...")
        self.btn = QPushButton("Send", self)

        top = QVBoxLayout(self)
        top.addWidget(self.text_edit, 1)
        row = QHBoxLayout()
        row.addWidget(self.line_edit, 1)
        row.addWidget(self.btn)
        top.addLayout(row)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Terminal")

        self.setup_ui()

        self.iostream = IOStream()
        self.iostream.text_written.connect(self.text_edit.appendPlainText)

        self.btn.clicked.connect(self._send_text)
        self.line_edit.returnPressed.connect(self._send_text)

    def showEvent(self, event) -> None:
        self.text_edit.clear()
        self.line_edit.clear()
        self.line_edit.setFocus()
        # 打开流
        self.iostream.open()
        super().showEvent(event)

    def closeEvent(self, event) -> None:
        # 关闭流
        self.iostream.close()
        super().closeEvent(event)

    # 内部方法

    def _send_text(self) -> None:
        s = self.line_edit.text()
        if not s:
            return
        self.text_edit.appendPlainText(s)
        self.iostream.push(s)
        self.line_edit.clear()

    def execute(self, func: Callable[..., _T], *args, **kwargs) -> _T:
        app = QApplication.instance()

        self.show()

        result = error = None
        loop = QEventLoop()

        def _execute():
            nonlocal result, error
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                error = e
            finally:
                loop.quit()

        t = threading.Thread(target=_execute, daemon=True)
        t.start()

        loop.exec()

        if error is not None:
            raise error

        return result

# 测试

def test_logic(stream: IOStream):
    # 现在你可以像使用普通文件一样使用 stream
    stream.write("System: Please enter your name.")
    name = stream.readline()
    
    stream.write(f"System: Processing data for {name}...")
    # 模拟耗时操作
    import time
    time.sleep(20)
    
    stream.write("System: Done!")
    return f"Processed_{name}"


if __name__ == "__main__":
    app = QApplication(sys.argv)
    terminal = Terminal()
    result = terminal.execute(test_logic, terminal.iostream)
    print("Result:", result)
    sys.exit(app.exec())


