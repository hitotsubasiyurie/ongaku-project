from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QShortcut, QKeySequence, QIcon, QAction
from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QStackedWidget, QMenu

from ongaku.core.settings import global_settings
from ongaku.core.kanban import KanBan, ThemeKanBan
from ongaku.ui.utils import with_busy_cursor
from ongaku.ui.page0.theme_box_widget import ThemeBoxWidget
from ongaku.ui.page0.page0_widget import Page0Widget
from ongaku.ui.page1.page1_widget import Page1Widget
from ongaku.ui.page2.page2_widget import Page2Widget


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

        self.page_btn = QPushButton(QIcon(f"./assets/{global_settings.ui_color_theme}/page.png"), "", parent=self)
        self.page_btn.setFixedSize(fh*1.5, fh*1.5)
        self.page_btn.setIconSize(self.page_btn.size())

        self.toolkit_btn = QPushButton(QIcon(f"./assets/{global_settings.ui_color_theme}/toolkit.png"), "", parent=self)
        self.toolkit_btn.setFixedSize(fh*1.5, fh*1.5)
        self.toolkit_btn.setIconSize(self.toolkit_btn.size())

        btn_qss = f"""
QPushButton {{
    /* 透明背景 */
    background-color: rgba(100, 100, 100, 0);
    /* 50% 圆角 */
    border-radius: {fh*0.75}px;
}}

QPushButton:hover {{
    /* 悬浮 */
    background-color: rgba(100, 100, 100, 200);
}}
"""
        [b.setStyleSheet(btn_qss) for b in [self.page_btn, self.toolkit_btn]]

    def setup_event(self) -> None:
        # 初始化 事件
        self.page_btn.clicked.connect(self._show_menu)
        self.toolkit_btn.clicked.connect(self._on_toolkit_btn_clicked)
        self.stack.currentChanged.connect(self._set_btns_geometry)
        self.page0.theme_kanban_selected.connect(self._on_theme_kanban_selected)

    def setup_shortcut(self) -> None:
        # 初始化 快捷键
        shortcut = QShortcut(Qt.Key.Key_Tab, self, activated=lambda: self.stack.setCurrentIndex((self.stack.currentIndex()+1)%3))
        shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        shortcut = QShortcut(Qt.Key.Key_F5, self, activated=self.refresh_kanban)

    def setup_context_menu(self) -> None:
        # 初始化 页面菜单
        self.menu = QMenu()
        action_page0 = self.menu.addAction("Theme Kanban")
        action_page0.triggered.connect(lambda: self.stack.setCurrentIndex(0))
        action_page1 = self.menu.addAction("Album Kanban")
        action_page1.triggered.connect(lambda: self.stack.setCurrentIndex(1))
        action_page2 = self.menu.addAction("Track Kanban")
        action_page2.triggered.connect(lambda: self.stack.setCurrentIndex(2))

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.kanban: KanBan = None

        self.setup_ui()
        self.setup_event()
        self.setup_shortcut()
        self.setup_context_menu()

    def set_kanban(self, kanban: KanBan) -> None:
        self.kanban = kanban
        self.page0.set_kanban(kanban)

    def refresh_kanban(self) -> None:
        if not self.kanban:
            return
        # self.current_theme_kanban.scan()
        # self.theme_box.set_kanban(self.kanban)
        # self.page1.set_theme_kanban(self.current_theme_kanban)
        # self.page2.set_theme_kanban(self.current_theme_kanban)

    # 重写方法

    def resizeEvent(self, event):
        self._set_btns_geometry()
        super().resizeEvent(event)

    # 内部方法

    def _show_menu(self) -> None:
        # 菜单显示在按钮左下角
        pos = self.page_btn.mapToGlobal(QPoint(0, self.page_btn.height()))
        self.menu.exec(pos)

    def _set_btns_geometry(self):
        index = self.stack.currentIndex()
        if index == 2:
            self.page_btn.move(0, 0)
            self.toolkit_btn.move(self.page_btn.width(), 0)
        else:
            self.page_btn.move(self.width() - self.page_btn.width(), 0)
            self.toolkit_btn.move(self.width() - self.page_btn.width()*2, 0)
    
    @with_busy_cursor
    def _on_toolkit_btn_clicked(self):
        pass

    # 事件动作

    @with_busy_cursor
    def _on_theme_kanban_selected(self) -> None:
        tk = self.kanban.theme_kanbans[self.page0.current_theme_kanban_p]
        self.page1.set_theme_kanban(tk)
        self.page2.set_theme_kanban(tk)
