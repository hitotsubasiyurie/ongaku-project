import sys
import time
from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QLabel
from PySide6.QtCore import QTimer, Qt


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Busy Cursor Demo")

        self.label = QLabel("点击按钮开始耗时操作")
        self.button = QPushButton("开始任务")
        self.button.clicked.connect(self.start_task)

        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(self.button)

    def start_task(self):
        # 设置鼠标为繁忙状态
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.label.setText("正在执行耗时任务...")

        # 用 QTimer.singleShot 模拟一个耗时操作（阻塞）
        QTimer.singleShot(100, self.long_task)

    def long_task(self):
        # 模拟耗时操作（阻塞3秒）
        time.sleep(3)

        # 恢复鼠标
        QApplication.restoreOverrideCursor()
        self.label.setText("任务完成！")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
