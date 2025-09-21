from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QWidget, QGridLayout, QLineEdit, QAbstractItemView

from ongaku.kanban.kanban import ThemeKanBan
from ongaku.kanban.page2.play_table_view import TrackTableView
from ongaku.kanban.page2.music_player_bar import MusicPlayerBar


class Page2Widget(QWidget):

    def setup_ui(self) -> None:
        # 初始化 UI
        grid_layout = QGridLayout()
        self.setLayout(grid_layout)
        grid_layout.setSpacing(5)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        self.title_field = QLineEdit()
        self.title_field.setPlaceholderText("Search title...")
        grid_layout.addWidget(self.title_field, 0, 1, 1, 1)

        self.artist_field = QLineEdit()
        self.artist_field.setPlaceholderText("Search artist...")
        grid_layout.addWidget(self.artist_field, 0, 2, 1, 1)

        self.album_field = QLineEdit()
        self.album_field.setPlaceholderText("Search album...")
        grid_layout.addWidget(self.album_field, 0, 3, 1, 1)

        self.date_field = QLineEdit()
        self.date_field.setPlaceholderText("Search date...")
        grid_layout.addWidget(self.date_field, 0, 4, 1, 1)

        self.mark_field = QLineEdit()
        self.mark_field.setPlaceholderText("Search mark...")
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
        self.title_field.textChanged.connect(lambda t: self.track_table_view.item_model.set_filter(1, t))
        self.artist_field.textChanged.connect(lambda t: self.track_table_view.item_model.set_filter(2, t))
        self.album_field.textChanged.connect(lambda t: self.track_table_view.item_model.set_filter(3, t))
        self.date_field.textChanged.connect(lambda t: self.track_table_view.item_model.set_filter(4, t))
        self.mark_field.textChanged.connect(lambda t: self.track_table_view.item_model.set_filter(5, t))
        self.track_table_view.doubleClicked.connect(self._on_track_table_double_clicked)
        self.track_table_view.favourite_selected.connect(lambda: self._set_track_mark("1", force=True))
        self.track_table_view.unfavourite_selected.connect(lambda: self._set_track_mark("0", force=True))
        self.track_table_view.clear_selected.connect(lambda: self._set_track_mark("", force=True))
        self.track_table_view.item_model.dataChanged.connect(lambda: self.theme_kanban.save_metadata_file())
        self.music_player_bar.playback_finished.connect(self._on_playback_finished)
        self.music_player_bar.prev_btn.clicked.connect(lambda: [self._search_no_mark_ix(-1), self._play()])
        self.music_player_bar.next_btn.clicked.connect(lambda: [self._search_no_mark_ix(1), self._play()])

    def setup_shortcut(self) -> None:
        # 初始化 快捷键
        QShortcut(Qt.Key.Key_Space, self, activated=self.music_player_bar.toggle_play)
        QShortcut(Qt.Key.Key_Left, self, activated=lambda: self.music_player_bar.skip(-3000))
        QShortcut(Qt.Key.Key_Right, self, activated=lambda: self.music_player_bar.skip(3000))
        # 主键盘 和 小键盘 Enter
        for key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            QShortcut(key, self, activated=self._play_selected)
        QShortcut(QKeySequence("Alt+Up"), self, activated=lambda: [self._search_no_mark_ix(-1), self._play()])
        QShortcut(QKeySequence("Alt+Down"), self, activated=lambda: [self._search_no_mark_ix(1), self._play()])
        QShortcut(QKeySequence("Alt+-"), self, activated=lambda: self._set_track_mark("0"))
        QShortcut(QKeySequence("Alt++"), self, activated=lambda: self._set_track_mark("1"))
        QShortcut(Qt.Key.Key_Escape, self, activated=
                  lambda: [x.clear() for x in [self.title_field, self.artist_field, self.album_field, self.date_field, self.mark_field]])
        QShortcut(Qt.Key.Key_Period, self, activated=self._hightlight_playing_ix)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.theme_kanban: ThemeKanBan = None
        # 内部属性
        # 当前播放 视图索引
        self._playing_ix: QModelIndex = None

        self.setup_ui()
        self.setup_event()
        self.setup_shortcut()

    def set_theme_kanban(self, theme_kanban: ThemeKanBan = None) -> None:
        self.theme_kanban = theme_kanban
        self._playing_ix = None
        # 清空搜索框
        [x.clear() for x in [self.title_field, self.artist_field, self.album_field, self.date_field, self.mark_field]]
        self.track_table_view.item_model.set_theme_kanban(theme_kanban)

    # 内部方法

    def _set_track_mark(self, rows: list[int] = [], mark: str = "", force: bool = False) -> None:
        rows = rows or list(sorted(set(i.row() for i in self.track_table_view.selectedIndexes())))
        # 批量处理
        for r in rows:
            p = self.track_table_view.item_model.layout_ps[r]
            if self.track_table_view.item_model.table[p][5] and not force:
                continue
            # 更新 看板
            i, j = self.track_table_view.item_model.kanban_index[p]
            self.theme_kanban.album_kanbans[i].album.tracks[j].mark = mark
            # 更新 视图
            self.track_table_view.item_model.table[p][5] = mark
            ix = self.track_table_view.item_model.index(r, 5)
            self.track_table_view.item_model.dataChanged.emit(ix, ix)
        # 保存文件
        self.theme_kanban.save_metadata_file()

    def _play_selected(self) -> None:
        ixs = self.track_table_view.selectedIndexes()
        if not ixs:
            return
        # 播放选择的第一个
        self._playing_ix = ixs[0]
        self._play()

    def _play(self) -> None:
        # index 无效 清空播放器
        if not self._playing_ix or not self._playing_ix.isValid():
            self.music_player_bar.set_media("")
            return

        row = self._playing_ix.row()
        p = self.track_table_view.item_model.layout_ps[row]
        i, j = self.track_table_view.item_model.kanban_index[p]
        file = self.theme_kanban.album_kanbans[i].track_files[j]
        self._hightlight_playing_ix()
        # 播放
        self.music_player_bar.set_media(file)
        # 更新 track mark
        self._set_track_mark([row], "0", force=False)

        # file 为空时
        if not file:
            self._on_playback_finished()

    def _hightlight_playing_ix(self) -> None:
        self.track_table_view.clearSelection()
        
        if not self._playing_ix or not self._playing_ix.isValid():
            return
        
        # track table 选中 当前播放行
        self.track_table_view.selectRow(self._playing_ix.row())
        self.track_table_view.setCurrentIndex(self._playing_ix)
        self.track_table_view.scrollTo(self._playing_ix, QAbstractItemView.ScrollHint.PositionAtCenter)

    def _on_playback_finished(self) -> None:
        # 清空播放器
        self.music_player_bar.set_media("")
        # 高光下一行
        row = self._playing_ix.row()
        self._playing_ix = self._playing_ix.siblingAtRow(row + 1)
        self._hightlight_playing_ix()
    
    def _search_no_mark_ix(self, direction: int) -> None:
        if not self._playing_ix or not self._playing_ix.isValid():
            return
        
        while True:
            row = self._playing_ix.row()
            self._playing_ix = self._playing_ix.siblingAtRow(row + direction)

            # 至尽头，退出循环
            if not self._playing_ix.isValid():
                break

            p = self.track_table_view.item_model.layout_ps[row]
            i, j = self.track_table_view.item_model.kanban_index[p]
            
            # 无 mark 信息，且有文件，退出循环
            if (not self.theme_kanban.album_kanbans[i].album.tracks[j].mark 
                and self.theme_kanban.album_kanbans[i].track_files[j]):
                break

    def _on_track_table_double_clicked(self, index: QModelIndex) -> None:
        # 双击 Size 列 播放
        if index.column() != 0:
            return
        self._playing_ix = index
        self._play()

