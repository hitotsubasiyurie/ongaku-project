from typing import Optional

from PySide6.QtCore import Qt, QModelIndex, Signal, QTimer
from PySide6.QtGui import QShortcut
from PySide6.QtWidgets import QWidget, QGridLayout, QLineEdit

from src.core.kanban import Kanban
from src.core.i18n import MESSAGE
from src.ui.page1.theme_table_view import ThemeTableView


class Page1Widget(QWidget):

    theme_kanban_played = Signal()

    def setup_ui(self) -> None:
        """初始化 UI"""
        grid_layout = QGridLayout()
        self.setLayout(grid_layout)
        grid_layout.setSpacing(5)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        self.name_field = QLineEdit()
        self.name_field.setPlaceholderText(MESSAGE.UI_20251231_170000)
        grid_layout.addWidget(self.name_field, 0, 1, 1, 1)

        self.theme_table_view = ThemeTableView()
        grid_layout.addWidget(self.theme_table_view, 1, 0, 1, 3)

        col_stretch = [1, 8, 8]
        [s and grid_layout.setColumnStretch(i, s) for i, s in enumerate(col_stretch)]

    def setup_event(self) -> None:
        """初始化 事件"""
        self.name_field.textChanged.connect(lambda t: self.theme_table_view.item_model.set_filter(1, t))
        self.theme_table_view.doubleClicked.connect(self._on_theme_table_double_clicked)

    def setup_shortcut(self) -> None:
        """初始化 快捷键"""
        QShortcut(Qt.Key.Key_Escape, self, activated=lambda: [x.clear() for x in [self.name_field]])
        # 主键盘 和 小键盘 Enter
        for key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            QShortcut(key, self, activated=self._play_theme_kanban)
        QShortcut(Qt.Key.Key_Period, self, activated=
                  lambda: self.theme_table_view.hightlight_row(self.theme_table_view.item_model.locate_playing_row()))

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.kanban: Optional[Kanban] = None
        # 当前播放的主题看板 指针
        self.playing_p: Optional[int] = None

        self.setup_ui()
        self.setup_event()
        self.setup_shortcut()

    def set_kanban(self, kanban: Kanban = None) -> None:
        self.kanban = kanban
        self.theme_table_view.item_model.reset_kanban(kanban)
        self.theme_table_view.hightlight_row(0)

    # 内部方法

    def _play_theme_kanban(self) -> None:
        ps = self.theme_table_view.get_selected_ps()
        if not ps:
            return
        
        p = ps[0]
        self.playing_p = self.theme_table_view.item_model.playing_p = p
        # 更新视图 垂直表头
        self.theme_table_view.verticalHeader().viewport().update()
        self.theme_kanban_played.emit()

    # 事件动作

    def _on_theme_table_double_clicked(self, index: QModelIndex) -> None:
        # 双击 Path 列 选择主题
        if index.column() != 0:
            return
        self._play_theme_kanban()


