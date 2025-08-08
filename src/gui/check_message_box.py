
from PySide6.QtCore import (Qt, QEvent, QObject, )
from PySide6.QtGui import (QPixmap, QResizeEvent, QKeyEvent, )
from PySide6.QtWidgets import (QWidget, QLineEdit, QLabel, QGridLayout, QMessageBox, QGraphicsOpacityEffect, 
    QScrollArea, QPlainTextEdit, )


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
        
        # 滚动区域和文本框
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFixedSize(400, 400)

        text_edit = QPlainTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(text)
        # 不自动换行
        text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        scroll.setWidget(text_edit)
        layout.addWidget(scroll, 0, 0)


