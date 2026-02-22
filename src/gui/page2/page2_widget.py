import os
import webbrowser
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QShortcut
from PySide6.QtWidgets import QGridLayout, QLineEdit, QWidget

from src.core.i18n import MESSAGE
from src.core.kanban import ThemeKanban
from src.core.settings import settings
from src.core.storage import COVER_NAME, AUDIO_EXTS, track_stemnames
from src.external import open_in_explorer, copy_to_clipboard
from src.gui.common import with_busy_cursor
from src.gui.features.put_away_resource import put_away_cover_file, put_away_track_file, \
    put_away_track_files
from src.gui.notifier import show_toast_msg, show_confirm_msg
from src.gui.page2.album_table_view import AlbumTableView
from src.gui.page2.cover_label import CoverLabel
from src.gui.page2.link_combo_box import LinkComboBox
from src.gui.page2.track_table_view import TrackTableView
from src.utils import convert_to_png, PILLOW_IMG_EXTS


class Page2Widget(QWidget):

    def setup_ui(self) -> None:
        """初始化 UI"""
        grid_layout = QGridLayout()
        self.setLayout(grid_layout)
        grid_layout.setSpacing(1)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        self.album_field = QLineEdit()
        self.album_field.setPlaceholderText(MESSAGE.UI_20251231_180000)
        grid_layout.addWidget(self.album_field, 0, 0, 1, 1)

        self.catno_field = QLineEdit()
        self.catno_field.setPlaceholderText(MESSAGE.UI_20251231_180001)
        grid_layout.addWidget(self.catno_field, 0, 1, 1, 1)

        self.date_field = QLineEdit()
        self.date_field.setPlaceholderText(MESSAGE.UI_20251231_180003)
        grid_layout.addWidget(self.date_field, 0, 2, 1, 1)

        self.track_field = QLineEdit()
        self.track_field.setPlaceholderText(MESSAGE.UI_20251231_180004)
        grid_layout.addWidget(self.track_field, 0, 3, 1, 1)

        self.link_box = LinkComboBox()
        grid_layout.addWidget(self.link_box, 0, 4, 1, 1)

        self.album_table_view = AlbumTableView()
        grid_layout.addWidget(self.album_table_view, 1, 0, 1, 3)

        self.track_table_view = TrackTableView()
        grid_layout.addWidget(self.track_table_view, 1, 3, 1, 3)

        col_stretch = [5, 1, 1, 2, 2, 1]
        [s and grid_layout.setColumnStretch(i, s) for i, s in enumerate(col_stretch)]

        self.cover_label = CoverLabel(self)

    def setup_event(self) -> None:
        """初始化 事件"""
        # 搜索框
        self.album_field.textChanged.connect(lambda t: self.album_table_view.item_model.set_filter(1, t))
        self.catno_field.textChanged.connect(lambda t: self.album_table_view.item_model.set_filter(2, t))
        self.date_field.textChanged.connect(lambda t: self.album_table_view.item_model.set_filter(3, t))
        self.track_field.textChanged.connect(lambda t: self.album_table_view.item_model.set_filter(100, t))
        # album_table_view 选中
        self.album_table_view.selectionModel().selectionChanged.connect(self._on_album_view_selected)
        # view 拖入路径
        self.album_table_view.paths_dropped.connect(self._on_paths_dropped)
        self.track_table_view.paths_dropped.connect(self._on_paths_dropped)
        # view 右键菜单动作
        self.track_table_view.action_copy_filename_clicked.connect(self._action_copy_filename)
        self.album_table_view.action_edit_clicked.connect(self._action_edit)
        self.album_table_view.action_delete_clicked.connect(self._action_delete)
        self.album_table_view.action_locate_clicked.connect(self._action_locate)
        self.album_table_view.action_search_cover_clicked.connect(self._action_search_cover)
        # view 编辑数据
        self.track_table_view.item_model.dataChanged.connect(self._save_timer.start)
        self.album_table_view.item_model.dataChanged.connect(self._save_timer.start)
        # cover_label 输入封面
        self.cover_label.image_pasted.connect(self._on_image_pasted)
        # link_box 输入链接
        self.link_box.link_added.connect(self._save_timer.start)

    def setup_shortcut(self) -> None:
        """初始化 快捷键"""
        QShortcut(Qt.Key.Key_Escape, self, activated=
            lambda: [x.clear() for x in [self.album_field, self.catno_field, self.date_field, self.track_field]])
        QShortcut(Qt.Key.Key_QuoteLeft, self, activated=self.cover_label.change_opacity)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.theme_kanban: Optional[ThemeKanban] = None

        # 保存元数据文件 防抖定时器 10 秒
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(10000)
        self._save_timer.timeout.connect(lambda: [show_toast_msg(MESSAGE.UI_20251231_180010), 
                                                  with_busy_cursor(self.theme_kanban.save_metadata_file)()])

        self.setup_ui()
        self.setup_event()
        self.setup_shortcut()

    def set_theme_kanban(self, theme_kanban: ThemeKanban = None) -> None:
        self.theme_kanban = theme_kanban
        # 清空搜索框
        [x.clear() for x in [self.album_field, self.catno_field, self.date_field, self.track_field]]
        self.cover_label.set_album_kanban(None)
        self.album_table_view.item_model.reset_theme_kanban(theme_kanban)
        self.track_table_view.item_model.reset_album_kanban(None)
        self.album_table_view.hightlight_row(0)

    # 事件动作

    @with_busy_cursor
    def _on_image_pasted(self, data: bytes) -> None:
        if not self.cover_label.album_kanban:
            return

        os.makedirs(self.cover_label.album_kanban.album_dir, exist_ok=True)
        Path(self.cover_label.album_kanban.album_dir, COVER_NAME).write_bytes(convert_to_png(data))
        self.cover_label.album_kanban.refresh()
        self.album_table_view.viewport().update()
        self.cover_label.set_album_kanban(self.cover_label.album_kanban)

    def _on_album_view_selected(self, *args, **kwargs) -> None:
        ps = self.album_table_view.get_selected_ps()
        if not ps:
            return
        
        # 多选行时不更新
        if len(ps) > 1:
            return

        # 更新组件
        album_kanban = self.theme_kanban.album_kanbans[ps[0]]
        self.track_table_view.item_model.reset_album_kanban(album_kanban)
        self.cover_label.set_album_kanban(album_kanban)
        self.link_box.set_album_kanban(album_kanban)

    def _action_copy_filename(self) -> None:
        if not self.track_table_view.item_model.album_kanban:
            return
        ps = self.track_table_view.get_selected_ps()
        filenames = track_stemnames(self.track_table_view.item_model.album_kanban.album)
        text = "\n".join(filenames[p] for p in ps)
        copy_to_clipboard(text)

    def _action_edit(self) -> None:
        """
        打开 主题 元数据文件。
        """
        if not self.theme_kanban:
            return
        os.startfile(self.theme_kanban.theme_metadata_file)

    def _action_delete(self) -> None:
        """
        删除所选 album 。
        """
        if not self.theme_kanban:
            return
        ps = self.album_table_view.get_selected_ps()
        if not ps:
            return
        if any(self.theme_kanban.album_kanbans[p].album_res_state for p in ps):
            show_toast_msg("Albums with resources cannot be deleted.", 2)
            return
        if not show_confirm_msg(f"Delete {len(ps)} albums?"):
            return
        self.theme_kanban.album_kanbans = [ak for i, ak in enumerate(self.theme_kanban.album_kanbans) 
                                           if i not in ps]
        self.theme_kanban.save_metadata_file()
        self.set_theme_kanban(self.theme_kanban)

    def _action_locate(self) -> None:
        """打开所选 album 的资源位置"""
        if not self.theme_kanban:
            return
        ps = self.album_table_view.get_selected_ps()
        if not ps:
            return
        p = ps[0]
        if os.path.isfile(self.theme_kanban.album_kanbans[p].album_archive):
            open_in_explorer(self.theme_kanban.album_kanbans[p].album_archive)
        else:
            open_in_explorer(self.theme_kanban.album_kanbans[p].album_dir)

    def _action_search_cover(self) -> None:
        """搜索所选 album 的封面"""
        if not self.theme_kanban:
            return
        
        sources = settings.ui_cov_sources
        country = settings.ui_cov_country

        ps = self.album_table_view.get_selected_ps()
        for p in ps:
            album = self.theme_kanban.album_kanbans[p].album.album
            url = f"https://www.google.com/search?q={album}&udm=2"
            webbrowser.open(url)
            url = f"https://covers.musichoarders.xyz/?sources={sources}&country={country}&album={album}"
            webbrowser.open(url)

    @with_busy_cursor
    def _on_paths_dropped(self, paths: list[str]) -> None:
        ps = self.album_table_view.get_selected_ps()
        # album view 至少 选中一个
        if not ps:
            return

        paths: list[Path] = list(map(Path, paths))
        albums = [self.theme_kanban.album_kanbans[p].album for p in ps]
        album_dirs = list(map(Path, [self.theme_kanban.album_kanbans[p].album_dir for p in ps]))

        # 选中多个 album item ，拖入多个文件夹，路径数量必须等于 album item 选中数
        if all(p.is_dir() for p in paths) and len(paths) == len(ps):
            # 按顺序匹配 album item 和文件夹
            for p, d, a in zip(paths, album_dirs, albums):
                src_files = [f for f in p.rglob("*") if f.suffix.lower() in AUDIO_EXTS]
                # 音频文件数量必须等于 tracks 数量
                if len(src_files) != len(a.tracks):
                    continue
                put_away_track_files(src_files, d, a)
            # 更新视图
            [self.theme_kanban.album_kanbans[p].refresh() for p in ps]
            self.album_table_view.viewport().update()
            return

        exts = set(p.suffix.lower() for p in paths)
        # 选中多个 album item ，拖入多个图片
        if exts.issubset(PILLOW_IMG_EXTS):
            # 路径数量等于 album view 选中数时
            if len(paths) == len(ps):
                [put_away_cover_file(*args) for args in zip(paths, album_dirs)]
            # 路径数量为一个时
            elif len(paths) == 1:
                [put_away_cover_file(paths[0], d) for d in album_dirs]
            # 更新视图
            [self.theme_kanban.album_kanbans[p].refresh() for p in ps]
            self.album_table_view.viewport().update()
            self.cover_label.set_album_kanban(self.theme_kanban.album_kanbans[ps[0]])
            return

        # 选中一个 album item ，选中多个 track item ，拖入多个音频文件
        if exts.issubset(AUDIO_EXTS) and len(ps) == 1:
            # 路径数量为一个时
            if len(paths) == 1:
                trackidx = self.track_table_view.selectedIndexes()[0].row()
                [put_away_track_file(p, d, albums[0], trackidx) for p, d in zip(paths, album_dirs)]
            # 路径数量为多个时
            else:
                put_away_track_files(paths, album_dirs[0], albums[0])
            # 更新视图
            self.theme_kanban.album_kanbans[ps[0]].refresh()
            self.album_table_view.viewport().update()
            self.track_table_view.viewport().update()

