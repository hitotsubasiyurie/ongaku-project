from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence, QIcon
from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout, QStackedWidget

from ongaku.core.settings import global_settings
from ongaku.core.kanban import KanBan, ThemeKanBan
from ongaku.kanban_ui.page0.theme_box_widget import ThemeBoxWidget
from ongaku.kanban_ui.page1.page1_widget import Page1Widget
from ongaku.kanban_ui.page2.page2_widget import Page2Widget


class Page0Widget(QWidget):

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

        self.page1 = Page1Widget()
        self.stack.addWidget(self.page1)
        self.page2 = Page2Widget()
        self.stack.addWidget(self.page2)

        self.page_btn_icons = [QIcon(f"./kanban_ui/assets/{global_settings.ui_color_theme}/page_next.png"), 
                               QIcon(f"./kanban_ui/assets/{global_settings.ui_color_theme}/page_prev.png")]
        self.page_btn = QPushButton(parent=self)
        self.page_btn.setIcon(self.page_btn_icons[0])
        self.page_btn.setFixedSize(fh*1.5, fh*1.5)
        self.page_btn.setIconSize(self.page_btn.size())

        self.theme_btn = QPushButton(QIcon(f"./kanban_ui/assets/{global_settings.ui_color_theme}/details.png"), "", parent=self)
        self.theme_btn.setFixedSize(fh*1.5, fh*1.5)
        self.theme_btn.setIconSize(self.theme_btn.size())

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
        [b.setStyleSheet(btn_qss) for b in [self.page_btn, self.theme_btn]]

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
        shortcut = QShortcut(Qt.Key.Key_Tab, self, activated=self._on_theme_btn_clicked)
        shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        shortcut = QShortcut(Qt.Key.Key_F5, self, activated=self.refresh_current_theme_kanban)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.kanban: KanBan = None
        self.current_theme_kanban: ThemeKanBan = None

        self.setup_ui()
        self.setup_event()
        self.setup_shortcut()

    def set_kanban(self, kanban: KanBan) -> None:
        self.kanban = kanban

    def refresh_current_theme_kanban(self) -> None:
        if not self.current_theme_kanban:
            return
        self.current_theme_kanban.scan()
        self.theme_box.set_kanban(self.kanban)
        self.page1.set_theme_kanban(self.current_theme_kanban)
        self.page2.set_theme_kanban(self.current_theme_kanban)

    # 重写方法

    def resizeEvent(self, event):
        self._set_btns_geometry()
        super().resizeEvent(event)

    # 内部方法

    def _toggle_page(self, dst: int = None):
        if not dst:
            dst = 0 if self.stack.currentIndex() == 1 else 1
        self.stack.setCurrentIndex(dst)
        self._set_btns_geometry()

    def _set_btns_geometry(self):
        index = self.stack.currentIndex()
        if index == 0:
            self.page_btn.setIcon(self.page_btn_icons[0])
            self.page_btn.move(self.width() - self.page_btn.width(), 0)
            self.theme_btn.move(self.width() - self.page_btn.width()*2, 0)
        else:
            self.page_btn.setIcon(self.page_btn_icons[1])
            self.page_btn.move(0, 0)
            self.theme_btn.move(self.page_btn.width(), 0)

    def _on_theme_btn_clicked(self):
        if self.theme_box.isHidden():
            self.theme_box.set_kanban(self.kanban)
            self.theme_box.move((self.width()-self.theme_box.width()) // 2, 
                                (self.height()-self.theme_box.height()) // 2)
            self.theme_box.show()
        else:
            self.theme_box.hide()

    def _on_theme_box_selected(self) -> None:
        self.current_theme_kanban = self.kanban.get_theme_kanban(self.theme_box.selected_theme)
        self.setWindowTitle(f"KanBan - {self.current_theme_kanban.theme_name if self.current_theme_kanban else ''}")
        self.page1.set_theme_kanban(self.current_theme_kanban)
        self.page2.set_theme_kanban(self.current_theme_kanban)



