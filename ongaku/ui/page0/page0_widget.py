from PySide6.QtCore import Qt, QModelIndex, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QWidget, QGridLayout, QLineEdit, QAbstractItemView

from ongaku.core.kanban import KanBan
from ongaku.ui.toast_notifier import toast_notify
from ongaku.ui.utils import with_busy_cursor
from ongaku.ui.page0.theme_table_view import ThemeTableView


class Page0Widget(QWidget):

    theme_kanban_selected = Signal()

    def setup_ui(self) -> None:
        # 初始化 UI
        grid_layout = QGridLayout()
        self.setLayout(grid_layout)
        grid_layout.setSpacing(5)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        self.name_field = QLineEdit()
        self.name_field.setPlaceholderText("search name...")
        grid_layout.addWidget(self.name_field, 0, 1, 1, 1)

        self.theme_table_view = ThemeTableView()
        grid_layout.addWidget(self.theme_table_view, 1, 0, 1, 3)

        col_stretch = [1, 8, 8]
        [s and grid_layout.setColumnStretch(i, s) for i, s in enumerate(col_stretch)]

    def setup_event(self) -> None:
        # 初始化 事件
        self.name_field.textChanged.connect(lambda t: self.theme_table_view.item_model.set_filter(1, t))
        self.theme_table_view.doubleClicked.connect(self._on_theme_table_double_clicked)

    def setup_shortcut(self) -> None:
        # 初始化 快捷键
        QShortcut(Qt.Key.Key_Escape, self, activated=lambda: [x.clear() for x in [self.name_field]])

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.kanban: KanBan = None
        # 当前选择的主题看板 指针
        self.current_theme_kanban_p: int = None

        self.setup_ui()
        self.setup_event()
        self.setup_shortcut()

    def set_kanban(self, kanban: KanBan = None) -> None:
        self.kanban = kanban
        self.theme_table_view.item_model.reset_kanban(kanban)

    #################### 内部方法 ####################

    def _on_theme_table_double_clicked(self, index: QModelIndex) -> None:
        # 双击 Path 列 选择主题
        if index.column() != 0:
            return
        self.theme_table_view.item_model.current_theme_kanban_p = self.theme_table_view.item_model.layout_ps[index.row()]
        self.current_theme_kanban_p = self.theme_table_view.item_model.current_theme_kanban_p
        # 更新视图 垂直表头
        self.theme_table_view.verticalHeader().viewport().update()
        self.theme_kanban_selected.emit()



