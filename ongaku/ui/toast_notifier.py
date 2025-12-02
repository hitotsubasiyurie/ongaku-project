from typing import Literal
from datetime import datetime

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt, QTimer, QEvent, QObject


INFO_LABEL_QSS = """
    /* 边框 1像素 实线 灰色半透明 */
    border: 1px solid rgba(192, 192, 192, 0.6);
    /* 圆角 */
    border-radius: 6px;
    /* 内边距 */
    padding: 4px;
"""

WARNNING_LABEL_QSS = """
    /* 边框 1像素 实线 灰色半透明 */
    border: 1px solid rgba(192, 192, 192, 0.6);
    /* 圆角 */
    border-radius: 6px;
    /* 内边距 */
    padding: 4px;
    /* 黄色背景 */
    background-color: rgba(255, 204, 0, 0.5);
"""

ERROR_LABEL_QSS = """
    /* 边框 1像素 实线 灰色半透明 */
    border: 1px solid rgba(192, 192, 192, 0.6);
    /* 圆角 */
    border-radius: 6px;
    /* 内边距 */
    padding: 4px;
    /* 红色背景 */
    background-color: rgba(204, 51, 51, 0.5);
"""


class ToastNotifier(QWidget):

    _instance: "ToastNotifier" = None

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)

        # 监听父类
        parent.installEventFilter(self)

        # 初始化 0 大小
        self.resize(0, 0)

        ToastNotifier._instance = self

    _LABEL_QSS = [INFO_LABEL_QSS, WARNNING_LABEL_QSS, ERROR_LABEL_QSS]

    def show_message(self, text: str, level: Literal[0, 1, 2]) -> None:
        """
        :param level: 级别。信息 0，警告 1，错误 2
        """
        label = QLabel(f"{datetime.now().strftime("%H:%M:%S")} {text}", self)
        # 高度固定
        label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        label.setStyleSheet(self._LABEL_QSS[level])
        self.layout().addWidget(label)
        # 展示，确定 label size
        label.show()

        # 5 秒后移除
        QTimer.singleShot(8000, lambda: self._remove_message(label))

        self.adjustSize()
        self._set_geometry()

    #################### 重写方法 ####################

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        # 布局存在元素时才需要适应位置
        if self.layout().count() and obj == self.parent():
            if event.type() in (QEvent.Type.Resize, QEvent.Type.Move):
                self._set_geometry()
        return super().eventFilter(obj, event)

    #################### 内部方法 ####################

    def _remove_message(self, label: QLabel):
        self.layout().removeWidget(label)
        label.deleteLater()
        self.adjustSize()
        self._set_geometry()

    def _set_geometry(self):
        parent: QWidget = self.parent()
        # 坐标 是相对于父类的
        x = parent.width() - self.width()
        y = parent.height() - self.height()
        self.move(x, y)


def toast_notify(text: str, level: Literal[0, 1, 2] = 0) -> None:
    if not ToastNotifier._instance:
        return
    
    ToastNotifier._instance.show_message(text, level)

