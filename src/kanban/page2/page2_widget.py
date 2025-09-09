from pathlib import Path

from PySide6.QtCore import Qt, QUrl, QModelIndex, QObject, QEvent
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QSlider, QPushButton, QLabel, QHeaderView, QStyleFactory, QGridLayout, 
    QLineEdit, QAbstractItemView, )


from src.kanban.kanban import ThemeKanBan
from src.kanban.page2.track_table_view import TrackTableView
from src.kanban.page2.music_player_bar import MusicPlayerBar


class PageWidget2(QWidget):

    def setup_ui(self) -> None:
        # 初始化 UI
        grid_layout = QGridLayout()
        self.setLayout(grid_layout)
        grid_layout.setSpacing(5)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        self.title_field = QLineEdit()
        grid_layout.addWidget(self.title_field, 0, 1, 1, 1)

        self.artist_field = QLineEdit()
        grid_layout.addWidget(self.artist_field, 0, 2, 1, 1)

        self.album_field = QLineEdit()
        grid_layout.addWidget(self.album_field, 0, 3, 1, 1)

        self.date_field = QLineEdit()
        grid_layout.addWidget(self.date_field, 0, 4, 1, 1)

        self.mark_field = QLineEdit()
        grid_layout.addWidget(self.mark_field, 0, 5, 1, 1)

        self.track_table_view = TrackTableView()
        grid_layout.addWidget(self.track_table_view, 1, 0, 1, 6)

        self.music_player_bar = MusicPlayerBar()
        grid_layout.addWidget(self.music_player_bar, 2, 1, 1, 3)

        row_stretch = [0, 1, 0]
        [s and grid_layout.setRowStretch(i, s) for i, s in enumerate(row_stretch)]

        col_stretch = [1, 8, 4, 4, 1, 1]
        [s and grid_layout.setColumnStretch(i, s) for i, s in enumerate(col_stretch)]

    def setup_event(self) -> None:
        # 初始化 事件
        self.title_field.textEdited.connect(lambda t: self.track_table_view.proxy_model.set_filter(1, t))
        self.artist_field.textEdited.connect(lambda t: self.track_table_view.proxy_model.set_filter(2, t))
        self.album_field.textEdited.connect(lambda t: self.track_table_view.proxy_model.set_filter(3, t))
        self.date_field.textEdited.connect(lambda t: self.track_table_view.proxy_model.set_filter(4, t))
        self.mark_field.textEdited.connect(lambda t: self.track_table_view.proxy_model.set_filter(5, t))
        self.track_table_view.doubleClicked.connect(self._on_track_table_double_clicked)
        self.music_player_bar.playback_finished.connect(self._play_next)
        self.music_player_bar.prev_btn.clicked.connect(self._play_prev)
        self.music_player_bar.next_btn.clicked.connect(self._play_next)

    def setup_shortcut(self) -> None:
        # 初始化 快捷键
        QShortcut(QKeySequence("Space"), self, activated=self.music_player_bar.toggle_play)
        # Ctrl+Up 无效
        QShortcut(QKeySequence("Alt+Up"), self, activated=self._play_prev)
        QShortcut(QKeySequence("Alt+Down"), self, activated=self._play_next)
        QShortcut(QKeySequence("Esc"), self, activated=
                  lambda: [x.setText("") for x in [self.title_field, self.artist_field, self.album_field, self.date_field, self.mark_field]])

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.theme_kanban: ThemeKanBan = None

        self.setup_ui()
        self.setup_event()
        self.setup_shortcut()

        # 内部属性
        self._playing_direction: int = 1
        self._playing_model_index: QModelIndex = None

    def set_theme_kanban(self, theme_kanban: ThemeKanBan = None) -> None:
        self.theme_kanban = theme_kanban
        self._playing_model_index = None
        self.track_table_view.source_model.set_theme_kanban(theme_kanban)
        self.track_table_view.proxy_model.unset_filter()
        self.track_table_view.proxy_model.sort(1, Qt.SortOrder.AscendingOrder)
        self.track_table_view.scrollToTop()

    # 内部方法

    def _play(self) -> None:
        while self._playing_model_index and self._playing_model_index.isValid():
            i, j = self.track_table_view.proxy_model.data(self._playing_model_index, Qt.ItemDataRole.UserRole)
            file = self.theme_kanban.album_kanbans[i].track_files[j]
            # 文件为空 继续寻找
            if not file:
                self._move_playing_index()
                continue

            self.music_player_bar.set_media(file)
            # 聚焦 track table 选中 当前播放行
            self.track_table_view.setFocus()
            self.track_table_view.scrollTo(self._playing_model_index, QAbstractItemView.ScrollHint.PositionAtCenter)
            self.track_table_view.clearSelection()
            self.track_table_view.selectRow(self._playing_model_index.row())
            return

        # index 无效 清空播放器
        self.music_player_bar.set_media("")
    
    def _play_prev(self) -> None:
        self._playing_direction = -1
        self._move_playing_index()
        self._play()

    def _play_next(self) -> None:
        self._playing_direction = 1
        self._move_playing_index()
        self._play()

    def _move_playing_index(self) -> None:
        if not self._playing_model_index:
            return
        row = self._playing_model_index.row()
        self._playing_model_index = self._playing_model_index.siblingAtRow(row + self._playing_direction)

    def _on_track_table_double_clicked(self, index: QModelIndex) -> None:
        # 双击 Size 列 播放
        if index.column() != 0:
            return
        self._playing_model_index = index
        self._play()
    
