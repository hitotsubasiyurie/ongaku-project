from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QIcon
from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QStackedWidget

from src.core.kanban import KanBan
from src.core.settings import global_settings
from src.lang import MESSAGE
from src.ui.common import BUTTON_QSS, with_busy_cursor
from src.ui.toast_notifier import toast_notify
from src.ui.page0.page0_widget import Page0Widget
from src.ui.page1.page1_widget import Page1Widget
from src.ui.page2.page2_widget import Page2Widget


class MainWindow(QWidget):

    def setup_ui(self) -> None:
        self.setWindowTitle("KanBan")
        # 字体高度
        fh = self.fontMetrics().height()

        # 初始化 UI
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.setSpacing(1)
        layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        self.page0 = Page0Widget()
        self.stack.addWidget(self.page0)
        self.page1 = Page1Widget()
        self.stack.addWidget(self.page1)
        self.page2 = Page2Widget()
        self.stack.addWidget(self.page2)

        self.page_prev_btn = QPushButton(QIcon(f"./assets/{global_settings.ui_color_theme}/page_prev.png"), "", parent=self)
        self.page_prev_btn.setFixedSize(fh*1.5, fh*1.5)
        self.page_prev_btn.setIconSize(self.page_prev_btn.size())

        self.page_next_btn = QPushButton(QIcon(f"./assets/{global_settings.ui_color_theme}/page_next.png"), "", parent=self)
        self.page_next_btn.setFixedSize(fh*1.5, fh*1.5)
        self.page_next_btn.setIconSize(self.page_next_btn.size())

        btn_qss = BUTTON_QSS.format(fh*0.75)
        [b.setStyleSheet(btn_qss) for b in [self.page_prev_btn, self.page_next_btn]]

    def setup_event(self) -> None:
        # 初始化 事件
        self.page_prev_btn.clicked.connect(lambda: self._change_page((self.stack.currentIndex()-1)%3))
        self.page_next_btn.clicked.connect(lambda: self._change_page((self.stack.currentIndex()+1)%3))
        self.page0.theme_kanban_selected.connect(self._on_theme_kanban_selected)

    def setup_shortcut(self) -> None:
        # 初始化 快捷键
        shortcut = QShortcut(Qt.Key.Key_Tab, self, activated=lambda: self._change_page((self.stack.currentIndex()+1)%3))
        shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        shortcut = QShortcut(Qt.Key.Key_F5, self, activated=self._refresh_kanban)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.kanban: KanBan = None

        self.setup_ui()
        self.setup_event()
        self.setup_shortcut()

    def set_kanban(self, kanban: KanBan) -> None:
        self.kanban = kanban
        self.page0.set_kanban(kanban)
        self.page1.set_theme_kanban(None)
        self.page2.set_theme_kanban(None)
        toast_notify(MESSAGE.UI_20251201_110005.format(kanban.album_collection_progress[0], kanban.track_mark_progress[0]))

    # 重写方法

    def resizeEvent(self, event):
        self._set_btns_geometry()
        super().resizeEvent(event)

    # 内部方法

    def _set_btns_geometry(self):
        index = self.stack.currentIndex()
        if index == 2:
            self.page_prev_btn.move(0, 0)
            self.page_next_btn.move(self.page_prev_btn.width(), 0)
        else:
            self.page_next_btn.move(self.width() - self.page_prev_btn.width(), 0)
            self.page_prev_btn.move(self.width() - self.page_prev_btn.width()*2, 0)

    # 事件动作

    @with_busy_cursor
    def _refresh_kanban(self) -> None:
        if not self.kanban:
            return
        self.kanban.scan()
        self.set_kanban(self.kanban)

    @with_busy_cursor
    def _change_page(self, index: int) -> None:
        self.kanban.invalidate_cache()
        self.stack.setCurrentIndex(index)
        self._set_btns_geometry()

    @with_busy_cursor
    def _on_theme_kanban_selected(self) -> None:
        tk = self.kanban.theme_kanbans[self.page0.current_theme_kanban_p]
        self.page1.set_theme_kanban(tk)
        self.page2.set_theme_kanban(tk)
        self.setWindowTitle(f"KanBan - {tk.theme_name}")
