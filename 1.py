from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QWidget
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QPoint
import sys


class Toast(QWidget):
    def __init__(self, parent, message, duration=3000):
        super().__init__(parent)

        self.setWindowFlags(Qt.WindowType.SubWindow | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # 标签显示消息
        self.label = QLabel(message, self)
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(50, 50, 50, 200);
                color: white;
                border-radius: 6px;
                padding: 8px 12px;
            }
        """)
        self.label.adjustSize()
        self.resize(self.label.size())

        # 定位到主窗口右下角
        parent_rect = parent.rect()
        x = parent_rect.width() - self.width() - 20
        y = parent_rect.height() - self.height() - 20
        self.move(x, y)

        # 淡入动画
        self.setWindowOpacity(0)
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.start()

        # 定时消失
        QTimer.singleShot(duration, self.fade_out)

    def fade_out(self):
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(600)
        self.animation.setStartValue(1)
        self.animation.setEndValue(0)
        self.animation.finished.connect(self.close)
        self.animation.start()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("主界面提示泡泡示例")
        self.resize(600, 400)

        # 测试：启动时弹出几个提示
        QTimer.singleShot(1000, lambda: self.show_toast("✅ 保存成功"))
        QTimer.singleShot(2000, lambda: self.show_toast("⚠️ 网络中断"))
        QTimer.singleShot(3000, lambda: self.show_toast("📢 新消息到达"))

    def show_toast(self, message):
        toast = Toast(self, message)
        toast.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
