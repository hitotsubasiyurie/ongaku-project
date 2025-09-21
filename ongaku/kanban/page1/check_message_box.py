
from PySide6.QtCore import (Qt, QEvent, QObject, )
from PySide6.QtGui import (QPixmap, QResizeEvent, QKeyEvent, )
from PySide6.QtWidgets import (QWidget, QLineEdit, QLabel, QGridLayout, QMessageBox, QGraphicsOpacityEffect, 
    QScrollArea, QPlainTextEdit, QApplication, )


class CheckMessageBox(QMessageBox):

    def __init__(self, title: str, text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)

        # 删除原有 QLabel
        layout: QGridLayout = self.layout()
        label = next((c for c in self.children() if isinstance(c, QLabel)), None)
        if label:
            self.layout().removeWidget(label)
            label.deleteLater()

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        
        # 滚动区域和文本框
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)

        # 设置滚动区域大小
        w, h = 600, 600
        scroll.setFixedSize(w, h)

        text_edit = QPlainTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(text)
        # 不自动换行
        text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        scroll.setWidget(text_edit)
        layout.addWidget(scroll, 0, 0)

    def showEvent(self, event):
        super().showEvent(event)
        # 获取屏幕尺寸
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        window_width = self.width()
        window_height = self.height()
        # 中心 展示
        self.move((screen_width - window_width) // 2, 
                 (screen_height - window_height) // 2)

