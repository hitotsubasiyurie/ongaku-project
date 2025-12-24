from typing import Literal

from PySide6.QtCore import Qt, QModelIndex, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QWidget, QGridLayout, QLineEdit

from src.core.kanban import ThemeKanBan
from src.ui.common import with_busy_cursor
from src.ui.page2.music_player_bar import MusicPlayerBar
from src.ui.page2.play_table_view import PlayTableView
from src.ui.toast_notifier import toast_notify


class Page2Widget(QWidget):

    def setup_ui(self) -> None:
        # 初始化 UI
        grid_layout = QGridLayout()
        self.setLayout(grid_layout)
        grid_layout.setSpacing(5)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        self.title_field = QLineEdit()
        self.title_field.setPlaceholderText("search title...")
        grid_layout.addWidget(self.title_field, 0, 1, 1, 1)

        self.artist_field = QLineEdit()
        self.artist_field.setPlaceholderText("search artist...")
        grid_layout.addWidget(self.artist_field, 0, 2, 1, 1)

        self.album_field = QLineEdit()
        self.album_field.setPlaceholderText("search album...")
        grid_layout.addWidget(self.album_field, 0, 3, 1, 1)

        self.date_field = QLineEdit()
        self.date_field.setPlaceholderText("search date...")
        grid_layout.addWidget(self.date_field, 0, 4, 1, 1)

        self.mark_field = QLineEdit()
        self.mark_field.setPlaceholderText("search mark...")
        grid_layout.addWidget(self.mark_field, 0, 5, 1, 1)

        self.play_table_view = PlayTableView()
        grid_layout.addWidget(self.play_table_view, 1, 0, 1, 6)

        self.music_player_bar = MusicPlayerBar()
        grid_layout.addWidget(self.music_player_bar, 2, 1, 1, 3)

        row_stretch = [0, 1, 0]
        [s and grid_layout.setRowStretch(i, s) for i, s in enumerate(row_stretch)]

        col_stretch = [1, 8, 4, 4, 1, 1]
        [s and grid_layout.setColumnStretch(i, s) for i, s in enumerate(col_stretch)]

    def setup_event(self) -> None:
        # 初始化 事件
        # 搜索框
        self.title_field.textChanged.connect(lambda t: self.play_table_view.item_model.set_filter(1, t))
        self.artist_field.textChanged.connect(lambda t: self.play_table_view.item_model.set_filter(2, t))
        self.album_field.textChanged.connect(lambda t: self.play_table_view.item_model.set_filter(3, t))
        self.date_field.textChanged.connect(lambda t: self.play_table_view.item_model.set_filter(4, t))
        self.mark_field.textChanged.connect(lambda t: self.play_table_view.item_model.set_filter(5, t))
        # play_table_view 双击
        self.play_table_view.doubleClicked.connect(self._on_track_table_double_clicked)
        # play_table_view 右键菜单动作
        self.play_table_view.favourite_selected.connect(lambda: self._set_track_mark([], "1", force=True))
        self.play_table_view.unfavourite_selected.connect(lambda: self._set_track_mark([], "0", force=True))
        self.play_table_view.clear_selected.connect(lambda: self._set_track_mark([], "", force=True))
        # play_table_view 编辑
        self.play_table_view.item_model.dataChanged.connect(self._save_timer.start)
        # 播放器事件
        self.music_player_bar.playback_finished.connect(self._on_playback_finished)
        self.music_player_bar.prev_btn.clicked.connect(lambda: self._search_no_mark_ix(-1))
        self.music_player_bar.next_btn.clicked.connect(lambda: self._search_no_mark_ix(1))

    def setup_shortcut(self) -> None:
        # 初始化 快捷键
        QShortcut(Qt.Key.Key_Space, self, activated=self.music_player_bar.toggle_play)
        QShortcut(Qt.Key.Key_Left, self, activated=lambda: self.music_player_bar.skip(-3000))
        QShortcut(Qt.Key.Key_Right, self, activated=lambda: self.music_player_bar.skip(3000))
        # 主键盘 和 小键盘 Enter
        for key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            QShortcut(key, self, activated=self._play_selected)
        QShortcut(QKeySequence("Alt+Up"), self, activated=lambda: self._search_no_mark_ix(-1))
        QShortcut(QKeySequence("Alt+Down"), self, activated=lambda: self._search_no_mark_ix(1))
        QShortcut(QKeySequence("-"), self, activated=lambda: [self._set_track_mark([], "0", force=True), self.play_table_view.hightlight_row(self._select_next().row())])
        QShortcut(QKeySequence("+"), self, activated=lambda: [self._set_track_mark([], "1", force=True), self.play_table_view.hightlight_row(self._select_next().row())])
        QShortcut(Qt.Key.Key_Escape, self, activated=
                  lambda: [x.clear() for x in [self.title_field, self.artist_field, self.album_field, self.date_field, self.mark_field]])
        QShortcut(Qt.Key.Key_Period, self, activated=lambda: self.play_table_view.hightlight_row(self.play_table_view.item_model.locate_playing_row()))

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.theme_kanban: ThemeKanBan = None

        # 保存元数据文件 防抖定时器 5 秒
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(5000)
        self._save_timer.timeout.connect(lambda: [toast_notify("saved metadata file !"), 
                                                  with_busy_cursor(self.theme_kanban.save_metadata_file)()])

        self.setup_ui()
        self.setup_event()
        self.setup_shortcut()

    def set_theme_kanban(self, theme_kanban: ThemeKanBan = None) -> None:
        self.theme_kanban = theme_kanban
        # 清空搜索框
        [x.clear() for x in [self.title_field, self.artist_field, self.album_field, self.date_field, self.mark_field]]
        self.play_table_view.item_model.reset_theme_kanban(theme_kanban)

    # 内部方法

    def _set_track_mark(self, rows: list[int] = [], mark: str = "", force: bool = False) -> None:
        if rows:
            model_indexs = [self.play_table_view.item_model.createIndex(r, 5) for r in rows]
        else:
            model_indexs = list(ix for ix in self.play_table_view.selectedIndexes() if ix.column() == 5)
        
        for ix in model_indexs:
            if self.play_table_view.item_model.data(ix, Qt.ItemDataRole.EditRole) and not force:
                continue
            self.play_table_view.item_model.setData(ix, mark, Qt.ItemDataRole.EditRole)

    def _select_next(self) -> QModelIndex:
        ixs = self.play_table_view.selectedIndexes()
        if not ixs:
            return
        ix = ixs[-1]
        next_ix = ix.siblingAtRow(ix.row() + 1)

        return next_ix if next_ix.isValid() else ix

    def _play(self, row: int) -> None:
        p = self.play_table_view.item_model.layout_ps[row]
        i, j = self.play_table_view.item_model.kanban_ij[p]
        file = self.theme_kanban.album_kanbans[i].track_filenames[j]
        self.play_table_view.hightlight_row(row)
        # 播放
        self.music_player_bar.set_media(file)
        # 更新播放图标
        self.play_table_view.item_model.playing_ij = (i, j)
        self.play_table_view.verticalHeader().viewport().update()
        # 更新 track mark
        self._set_track_mark([row], "0", force=False)

        # file 为空时
        if not file:
            self._on_playback_finished()

    # 事件动作

    def _search_no_mark_ix(self, direction: Literal[-1, 1]) -> None:
        if not self.theme_kanban:
            return

        layout_ps = self.play_table_view.item_model.layout_ps

        rows = range(len(layout_ps)) if direction == 1 else reversed(range(len(layout_ps)))

        for row in rows:
            p = layout_ps[row]
            i, j = self.play_table_view.item_model.kanban_ij[p]

            if (not self.theme_kanban.album_kanbans[i].album.tracks[j].mark
                and self.theme_kanban.album_kanbans[i].track_filenames[j]):
                self.play_table_view.hightlight_row(row)
                break

        self.play_table_view.hightlight_row(row)

    def _on_track_table_double_clicked(self, index: QModelIndex) -> None:
        # 双击 Size 列 播放
        if index.column() != 0:
            return
        self._play(index.row())

    def _on_playback_finished(self) -> None:
        # 清空播放器
        self.music_player_bar.set_media("")
        # 高光下一行
        playing_row = self.play_table_view.item_model.locate_playing_row()
        playing_row is not None and self.play_table_view.hightlight_row(playing_row + 1)

    def _play_selected(self) -> None:
        ixs = self.play_table_view.selectedIndexes()
        if not ixs:
            return
        # 播放选择的第一个
        self._play(ixs[0].row())
