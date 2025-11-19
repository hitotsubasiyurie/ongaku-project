from PySide6.QtCore import Qt, QModelIndex, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QWidget, QGridLayout, QLineEdit, QAbstractItemView

from ongaku.core.kanban import KanBan
from ongaku.ui.toast_notifier import toast_notify
from ongaku.ui.utils import with_busy_cursor
from ongaku.ui.page0.theme_table_view import ThemeTableView


class Page0Widget(QWidget):

    def setup_ui(self) -> None:
        # 初始化 UI
        grid_layout = QGridLayout()
        self.setLayout(grid_layout)
        grid_layout.setSpacing(5)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        self.name_field = QLineEdit()
        self.name_field.setPlaceholderText("search title...")
        grid_layout.addWidget(self.name_field, 0, 1, 1, 1)

        self.theme_tree_view = ThemeTableView()
        grid_layout.addWidget(self.theme_tree_view, 1, 0, 1, 6)


    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.setup_ui()

    def set_kanban(self, kanban: KanBan = None) -> None:
        self.kanban = kanban
        self.theme_tree_view.item_model.reset_kanban(kanban)






