from datetime import datetime
from typing import Literal

from PySide6.QtCore import Qt, QTimer, QEvent, QObject
from PySide6.QtGui import QFontMetrics, QShowEvent
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy, QMessageBox, QGridLayout, \
    QPlainTextEdit, QApplication

################################################################################
### 弹窗消息
################################################################################


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

    def __init__(self, parent: QWidget) -> None:
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

    _LABEL_QSS = [INFO_LABEL_QSS, WARNNING_LABEL_QSS, ERROR_LABEL_QSS]

    def show_message(self, text: str, level: Literal[0, 1, 2]) -> None:
        label = QLabel(f"{datetime.now().strftime('%H:%M:%S')} {text}", self)
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


################################################################################
### 长消息
################################################################################


class LongMessageBox(QMessageBox):

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        # 删除原有 QLabel
        layout: QGridLayout = self.layout()
        for i in reversed(range(layout.count())):
            item = layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, QLabel):
                layout.removeWidget(widget)
                widget.deleteLater()

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        # 文本框
        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        # 不自动换行
        self.text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        layout.addWidget(self.text_edit, 0, 0)

    def setText(self, text) -> None:
        self.text_edit.setPlainText(text)

    def showEvent(self, event: QShowEvent) -> None:
        self._adjust_size()
        super().showEvent(event)
        # 中心 展示
        self.move(QApplication.primaryScreen().availableGeometry().center() - self.rect().center())

    # 内部方法

    def _adjust_size(self) -> None:
        # 获取屏幕尺寸
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        # text_edit 自适应尺寸
        fm = QFontMetrics(self.text_edit.font())
        lines = self.text_edit.toPlainText().split("\n")
        text_width = max((fm.horizontalAdvance(l) for l in lines))
        text_height = fm.lineSpacing() * (len(lines)+2)

        self.text_edit.setFixedSize(min(max(50, text_width + 50), screen_width*0.5),
                                    min(max(20, text_height), screen_height*0.6))

        self.adjustSize()


################################################################################
### 对外接口
################################################################################


_main_window: QWidget = None
_toast_notifier: ToastNotifier = None


def init_notifier(main_window: QWidget) -> None:
    global _main_window, _toast_notifier
    _main_window = main_window
    _toast_notifier = ToastNotifier(parent=main_window)


def show_toast_msg(text: str, level: Literal[0, 1, 2] = 0) -> None:
    """
    :param level: 级别。信息 0，警告 1，错误 2
    """
    if _toast_notifier is None:
        return

    _toast_notifier.show_message(text, level)


def show_dialog_msg(text: str, level: Literal[0, 1, 2] = 0, title: str = "") -> None:
    """
    :param level: 级别。信息 0，警告 1，错误 2。
    """
    msg = QMessageBox(_main_window)
    msg.setText(text)
    title = title or ("Info", "Warning", "Error")[level]
    msg.setWindowTitle(title)
    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
    # 对话框文字可选
    msg.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
    icon = (QMessageBox.Icon.Information, QMessageBox.Icon.Warning, QMessageBox.Icon.Critical)[level]
    msg.setIcon(icon)
    msg.exec()


def show_confirm_msg(text: str, title: str = "Confirm") -> bool:
    reply = QMessageBox.question(_main_window, title, text, 
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                 defaultButton=QMessageBox.StandardButton.No)
    return reply == QMessageBox.StandardButton.Yes


def show_dialog_long_msg(text: str, title: str = "Info") -> None:
    msg = LongMessageBox(_main_window)
    msg.setText(text)
    msg.setWindowTitle(title)
    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg.exec()


def show_confirm_long_msg(text: str, title: str = "Confirm") -> bool:
    msg = LongMessageBox(_main_window)
    msg.setText(text)
    msg.setWindowTitle(title)
    msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    msg.setDefaultButton(QMessageBox.StandardButton.No)
    return msg.exec() == QMessageBox.StandardButton.Yes


