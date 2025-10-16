from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt, QTimer, QEvent, QObject


BUBBLE_LABEL_QSS = """
    /* 边框 1像素 实线 灰色半透明 */
    border: 1px solid rgba(192, 192, 192, 0.6);
    /* 圆角 */
    border-radius: 6px;
    /* 内边距 */
    padding: 4px;
"""


class ToastNotifier(QWidget):

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

        # 字体小一号
        font = self.font()
        font.setPointSize(font.pointSize() - 1)
        self.setFont(font)

    def show_message(self, text: str):

        label = QLabel(text, self)
        # 高度固定
        label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        label.setStyleSheet(BUBBLE_LABEL_QSS)
        self.layout().addWidget(label)
        # 展示，确定 label size
        label.show()

        # 5 秒后移除
        QTimer.singleShot(5000, lambda: self._remove_message(label))

        self.adjustSize()
        self._set_geometry()

    # 重写方法

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        # 布局存在元素时才需要适应位置
        if self.layout().count() and obj == self.parent():
            if event.type() in (QEvent.Type.Resize, QEvent.Type.Move):
                self._set_geometry()
        return super().eventFilter(obj, event)

    # 内部方法

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
