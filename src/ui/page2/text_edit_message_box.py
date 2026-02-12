from PySide6.QtGui import QFontMetrics, QShowEvent
from PySide6.QtWidgets import QLabel, QGridLayout, QMessageBox, QPlainTextEdit, QApplication


class TextEditMessageBox(QMessageBox):

    def __init__(self, title: str, text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)

        # 删除原有 QLabel
        layout: QGridLayout = self.layout()
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and isinstance(widget:= item.widget(), QLabel):
                layout.removeWidget(widget)
                widget.deleteLater()

        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        
        # 文本框
        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        # 不自动换行
        self.text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.text_edit.setPlainText(text)

        layout.addWidget(self.text_edit, 0, 0)

        self._adjust_size(text)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        # 中心 展示
        self.move(QApplication.primaryScreen().availableGeometry().center() - self.rect().center())

    # 内部方法

    def _adjust_size(self, text: str) -> None:
        # 获取屏幕尺寸
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        # text_edit 自适应尺寸
        fm = QFontMetrics(self.font())
        lines = text.split("\n")
        text_width = max((fm.horizontalAdvance(l) for l in lines))
        text_height = fm.lineSpacing() * (len(lines)+2)

        self.text_edit.setFixedSize(min(max(50, text_width + 50), screen_width*0.5),
                                    min(max(20, text_height), screen_height*0.6))

        self.adjustSize()


    def show_message()
