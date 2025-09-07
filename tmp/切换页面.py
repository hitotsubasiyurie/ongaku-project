from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton,
    QVBoxLayout, QStackedWidget, QLabel
)
from PySide6.QtCore import Qt
import sys


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 中央容器
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)

        # 页面堆叠
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # 页面 1
        page1 = QLabel("这里是页面 1")
        page1.setAlignment(Qt.AlignCenter)
        page1.setStyleSheet("background-color: lightblue;")
        self.stack.addWidget(page1)

        # 页面 2
        page2 = QLabel("这里是页面 2")
        page2.setAlignment(Qt.AlignCenter)
        page2.setStyleSheet("background-color: lightgreen;")
        self.stack.addWidget(page2)

        # 漂浮切换按钮
        self.toggle_btn = QPushButton(">")
        self.toggle_btn.setParent(self)  # 直接挂在主窗口
        self.toggle_btn.resize(40, 40)
        self.toggle_btn.move(self.width() - 50, 10)  # 初始位置
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 100); /* 半透明 */
                color: white;
                border-radius: 20px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 160);
            }
        """)

        self.toggle_btn.clicked.connect(self.toggle_page)

        # 窗口大小变化时重新定位按钮
        self.resizeEvent = self.on_resize

    def toggle_page(self):
        index = self.stack.currentIndex()
        if index == 0:
            self.stack.setCurrentIndex(1)
            self.toggle_btn.setText("<")
        else:
            self.stack.setCurrentIndex(0)
            self.toggle_btn.setText(">")

    def on_resize(self, event):
        """保持按钮固定在右上角"""
        self.toggle_btn.move(self.width() - 50, 10)
        super().resizeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(500, 400)
    window.show()
    sys.exit(app.exec())
