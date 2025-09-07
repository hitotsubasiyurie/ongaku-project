from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QPixmap, QResizeEvent
from PySide6.QtWidgets import (QWidget, QPushButton, QVBoxLayout, QStackedWidget, )

from src.kanban.kanban import KanBan
from src.kanban.page1.page_widget import PageWidget1
from src.kanban.page2.page_widget import PageWidget2
from src.kanban.widgets.theme_box_widget import ThemeBoxWidget


class KanBanUI(QWidget):

    def setup_ui(self) -> None:
        # 字体高度
        fh = self.fontMetrics().height()

        # 初始化 UI
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        layout.setSpacing(1)
        layout.setContentsMargins(0, 0, 0, 0)

        self.page1 = PageWidget1()
        self.stack.addWidget(self.page1)
        self.page2 = PageWidget2()
        self.stack.addWidget(self.page2)

        self.page_btn = QPushButton(">", parent=self)
        self.page_btn.setObjectName("FloatButton")
        self.page_btn.setFixedSize(fh*2, fh*2)
        self.page_btn.move(self.width() - self.page_btn.width(), 0)

        self.theme_btn = QPushButton("≡", parent=self)
        self.theme_btn.setObjectName("FloatButton")
        self.theme_btn.setFixedSize(fh*2, fh*2)
        self.theme_btn.move(self.width() - self.page_btn.width()*2, 0)

        self.theme_box = ThemeBoxWidget(self)
        self.theme_box.hide()

    def setup_event(self) -> None:
        # 初始化 事件
        self.page_btn.clicked.connect(self._on_page_btn_clicked)
        self.theme_btn.clicked.connect(self._on_theme_btn_clicked)
        ## TODO : theme box 失去焦点 隐藏

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.kanban: KanBan = None

        self.setup_ui()
        self.setup_event()

    def set_kanban(self, kanban: KanBan) -> None:
        self.kanban = kanban
        self.theme_box.set_kanban(kanban)

    # 重写方法

    def resizeEvent(self, event):
        """保持按钮固定在右上角"""
        self.page_btn.move(self.width() - self.page_btn.width(), 0)
        self.theme_btn.move(self.width() - self.page_btn.width()*2, 0)
        super().resizeEvent(event)

    # 内部方法

    def _on_page_btn_clicked(self):
        index = self.stack.currentIndex()
        if index == 0:
            self.stack.setCurrentIndex(1)
            self.page_btn.setText("<")
            self.page_btn.move(0, 0)
        else:
            self.stack.setCurrentIndex(0)
            self.page_btn.setText(">")
            self.page_btn.move(self.width() - 50, 0)

    def _on_theme_btn_clicked(self):
        if self.theme_box.isHidden():
            self.theme_box.move((self.width()-self.theme_box.width()) // 2, 
                                (self.height()-self.theme_box.height()) // 2)
            self.theme_box.show()
            print("show")
        else:
            self.theme_box.hide()




