from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QPixmap, QResizeEvent, QShortcut, QKeySequence
from PySide6.QtWidgets import (QWidget, QPushButton, QVBoxLayout, QStackedWidget, )

from src.kanban.kanban import KanBan, ThemeKanBan
from src.kanban.page1.page1_widget import PageWidget1
from src.kanban.page2.page2_widget import PageWidget2
from src.kanban.widgets.theme_box_widget import ThemeBoxWidget


class KanBanUI(QWidget):

    def setup_ui(self) -> None:
        # 字体高度
        fh = self.fontMetrics().height()

        # 初始化 UI
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(1)
        layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        self.page1 = PageWidget1()
        self.stack.addWidget(self.page1)
        self.page2 = PageWidget2()
        self.stack.addWidget(self.page2)

        self.page_btn = QPushButton(">", parent=self)
        self.page_btn.setFixedSize(fh*2, fh*2)
        self.page_btn.setObjectName("FloatButton")

        self.theme_btn = QPushButton("≡", parent=self)
        self.theme_btn.setFixedSize(fh*2, fh*2)
        self.theme_btn.setObjectName("FloatButton")

        self.theme_box = ThemeBoxWidget(self)
        self.theme_box.hide()

    def setup_event(self) -> None:
        # 初始化 事件
        self.page_btn.clicked.connect(self._toggle_page)
        self.theme_btn.clicked.connect(self._on_theme_btn_clicked)
        self.theme_box.selected_changed.connect(self._on_theme_box_selected)

    def setup_shortcut(self) -> None:
        # 初始化 快捷键
        QShortcut(QKeySequence("Alt+Left"), self, activated=lambda : self._toggle_page(0))
        QShortcut(QKeySequence("Alt+Right"), self, activated=lambda : self._toggle_page(1))
        shortcut = QShortcut(QKeySequence("Tab"), self, activated=self._on_theme_btn_clicked)
        shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        shortcut = QShortcut(QKeySequence("F5"), self, activated=self.refresh_current_theme_kanban)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.kanban: KanBan = None
        self.current_theme_kanban: ThemeKanBan = None

        self.setup_ui()
        self.setup_event()
        self.setup_shortcut()

    def set_kanban(self, kanban: KanBan) -> None:
        self.kanban = kanban
        self.theme_box.set_kanban(kanban)

    def refresh_current_theme_kanban(self) -> None:
        if not self.current_theme_kanban:
            return
        self.current_theme_kanban.scan()
        self.page1.set_theme_kanban(self.current_theme_kanban)
        self.page2.set_theme_kanban(self.current_theme_kanban)

    # 重写方法

    def resizeEvent(self, event):
        self._locate_btns()
        super().resizeEvent(event)

    # 内部方法

    def _locate_btns(self):
        index = self.stack.currentIndex()
        if index == 0:
            self.page_btn.setText(">")
            self.page_btn.move(self.width() - self.page_btn.width(), 0)
            self.theme_btn.move(self.width() - self.page_btn.width()*2, 0)
        else:
            self.page_btn.setText("<")
            self.page_btn.move(0, 0)
            self.theme_btn.move(self.page_btn.width(), 0)

    def _toggle_page(self, dst: int = None):
        if not dst:
            dst = 0 if self.stack.currentIndex() == 1 else 1
        self.stack.setCurrentIndex(dst)
        self._locate_btns()

    def _on_theme_btn_clicked(self):
        if self.theme_box.isHidden():
            self.theme_box.move((self.width()-self.theme_box.width()) // 2, 
                                (self.height()-self.theme_box.height()) // 2)
            self.theme_box.show()
        else:
            self.theme_box.hide()

    def _on_theme_box_selected(self) -> None:
        self.current_theme_kanban = self.kanban.get_theme_kanban(self.theme_box.selected_theme)
        self.page1.set_theme_kanban(self.current_theme_kanban)
        self.page2.set_theme_kanban(self.current_theme_kanban)




