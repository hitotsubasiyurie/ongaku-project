import os
import shutil
import subprocess
import itertools
import webbrowser
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QShortcut
from PySide6.QtWidgets import QGridLayout, QLineEdit, QMessageBox, QWidget

from ongaku.core.basemodels import Album
from ongaku.core.settings import global_settings
from ongaku.core.constants import AUDIO_EXTS, IMG_EXTS
from ongaku.utils.audiofile_utils import analyze_resource_track
from ongaku.utils.basemodel_utils import tracks_assignment
from ongaku.core.kanban import ThemeKanBan, track_filenames
from ongaku.kanban_ui.toast_notifier import toast_notify
from ongaku.kanban_ui.utils import with_busy_cursor
from ongaku.kanban_ui.page1.album_table_view import AlbumTableView
from ongaku.kanban_ui.page1.text_edit_message_box import TextEditMessageBox
from ongaku.kanban_ui.page1.link_combo_box import LinkComboBox
from ongaku.kanban_ui.page1.track_table_view import TrackTableView
from ongaku.kanban_ui.page1.cover_label import CoverLabel


class Page1Widget(QWidget):

    def setup_ui(self) -> None:

        # 初始化 UI
        grid_layout = QGridLayout()
        self.setLayout(grid_layout)
        grid_layout.setSpacing(1)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        self.album_field = QLineEdit()
        self.album_field.setPlaceholderText("Search album...")
        grid_layout.addWidget(self.album_field, 0, 0, 1, 1)

        self.catno_field = QLineEdit()
        self.catno_field.setPlaceholderText("Search catno...")
        grid_layout.addWidget(self.catno_field, 0, 1, 1, 1)

        self.date_field = QLineEdit()
        self.date_field.setPlaceholderText("Search date...")
        grid_layout.addWidget(self.date_field, 0, 2, 1, 1)

        self.link_box = LinkComboBox()
        grid_layout.addWidget(self.link_box, 0, 3, 1, 1)

        self.album_table_view = AlbumTableView()
        grid_layout.addWidget(self.album_table_view, 1, 0, 1, 3)

        self.track_table_view = TrackTableView()
        grid_layout.addWidget(self.track_table_view, 1, 3, 1, 2)

        col_stretch = [5, 1, 1, 2, 3]
        [s and grid_layout.setColumnStretch(i, s) for i, s in enumerate(col_stretch)]

        self.cover_label = CoverLabel(self)

    def setup_event(self) -> None:
        # 初始化 事件
        # 搜索框
        self.album_field.textChanged.connect(lambda t: self.album_table_view.item_model.set_filter(1, t))
        self.catno_field.textChanged.connect(lambda t: self.album_table_view.item_model.set_filter(2, t))
        self.date_field.textChanged.connect(lambda t: self.album_table_view.item_model.set_filter(3, t))
        self.album_table_view.item_model.layoutChanged.connect(lambda: self.album_table_view.selectRow(0))
        self.album_table_view.selectionModel().selectionChanged.connect(self._on_album_view_selected)
        # view 拖入路径
        self.album_table_view.paths_dropped.connect(self._on_paths_dropped)
        self.track_table_view.paths_dropped.connect(self._on_paths_dropped)
        # album_table_view 右键菜单动作
        self.album_table_view.action_edit_clicked.connect(self._action_edit)
        self.album_table_view.action_delete_clicked.connect(self._action_delete)
        self.album_table_view.action_locate_clicked.connect(self._action_locate)
        self.album_table_view.action_search_cover_clicked.connect(self._action_search_cover)
        # view 编辑数据
        self.track_table_view.item_model.dataChanged.connect(self._save_timer.start)
        self.album_table_view.item_model.dataChanged.connect(self._save_timer.start)
        self.cover_label.image_pasted.connect(self._on_image_pasted)

    def setup_shortcut(self) -> None:
        # 初始化 快捷键
        QShortcut(Qt.Key.Key_Escape, self, activated=
            lambda: [x.clear() for x in [self.album_field, self.catno_field, self.date_field]])
        QShortcut(Qt.Key.Key_QuoteLeft, self, activated=self.cover_label.change_opacity)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.theme_kanban: ThemeKanBan = None

        # 保存元数据文件 防抖定时器 10 秒
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(10000)
        self._save_timer.timeout.connect(lambda: [toast_notify("saved metadata file !"), 
                                                  with_busy_cursor(self.theme_kanban.save_metadata_file)()])

        self.setup_ui()
        self.setup_event()
        self.setup_shortcut()

    def set_theme_kanban(self, theme_kanban: ThemeKanBan = None) -> None:
        self.theme_kanban = theme_kanban
        # 清空搜索框
        [x.clear() for x in [self.album_field, self.catno_field, self.date_field]]
        self.cover_label.set_album_kanban(None)
        self.album_table_view.item_model.reset_theme_kanban(theme_kanban)
        self.track_table_view.item_model.reset_album_kanban(None)

    # 内部方法

    def _putaway_cover_file(self, src: Path, dst_dir: Path) -> bool:
        dst_dir.mkdir(parents=True, exist_ok=True)
        ext = src.suffix.lower()
        dst = dst_dir / ("cover"+ext)
        shutil.copy2(src, dst)
        return True

    def _putaway_track_file(self, src: Path, dst_dir: Path, album: Album, trackidx: int) -> bool:
        dst_dir.mkdir(parents=True, exist_ok=True)
        ext = src.suffix.lower()
        dst = dst_dir / (track_filenames(album)[trackidx]+ext)
        src.rename(dst)
        return True

    def _putaway_track_files(self, src_files: list[Path], dst_dir: Path, album: Album) -> bool:
        dst_dir.mkdir(parents=True, exist_ok=True)

        src_tracks = list(map(analyze_resource_track, src_files))
        row_ind, col_ind, aver_similarity, _ = tracks_assignment(src_tracks, album.tracks)

        dst_names = track_filenames(album)
        _map: dict[Path, Path] = {src_files[r]: (dst_dir / (dst_names[c] + src_files[r].suffix.lower())) 
                                  for r, c in zip(row_ind, col_ind)}

        text = f"""
Directory:\t\t{src_files[0].parent.name}
Album:\t\t{album.album}
Average Similarity:\t{aver_similarity:.02f}
"""
        text += "\n"*2 + "\n".join(f"    {k.name}\n->  {v.name}\n" for k, v in _map.items())
        accept = self._ask_for_confirm("Check Again", text)
        
        if not accept:
            return False
        
        [src.rename(dst) for src, dst in _map.items()]
        return True

    def _ask_for_confirm(self, title: str, text: str, on_yes_clicked: Callable = None, 
                            on_no_clicked: Callable = None) -> bool:
        """弹出确认对话框"""
        check_msg = TextEditMessageBox(title, text, parent=self)
        check_msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        # 设置默认按钮为 NO
        check_msg.setDefaultButton(QMessageBox.StandardButton.No)
        on_yes_clicked and check_msg.button(QMessageBox.StandardButton.Yes).clicked.connect(on_yes_clicked)
        on_no_clicked and check_msg.button(QMessageBox.StandardButton.No).clicked.connect(on_no_clicked)
        # 阻塞
        accept = check_msg.exec() == QMessageBox.StandardButton.Yes
        return accept 

    @with_busy_cursor
    def _on_image_pasted(self, data: bytes) -> None:
        if not self.cover_label.album_kanban:
            return

        cover = self.cover_label.album_kanban.cover
        if cover:
            if not self._ask_for_confirm("Check Again", "Replace cover?"):
                return
            os.unlink(cover)

        os.makedirs(self.cover_label.album_kanban.album_dir, exist_ok=True)
        Path(self.cover_label.album_kanban.album_dir, "cover.png").write_bytes(data)
        self.cover_label.album_kanban.__post_init__()
        self.album_table_view.viewport().update()
        self.cover_label.set_album_kanban(self.cover_label.album_kanban)

    ## 事件动作

    def _on_album_view_selected(self, *args, **kwargs) -> None:
        ps = self.album_table_view.get_selected_ps()
        if not ps:
            return
        
        # 展示 所有已选 albums 的 links
        links = list(set(itertools.chain.from_iterable(self.theme_kanban.album_kanbans[p].album.links for p in ps)))
        self.link_box.set_links(links)

        # 多选行时不更新
        if len(ps) > 1:
            return

        # 展示 album 的 track, cover
        album_kanban = self.theme_kanban.album_kanbans[ps[0]]
        self.track_table_view.item_model.reset_album_kanban(album_kanban)
        self.cover_label.set_album_kanban(album_kanban)

    def _action_edit(self) -> None:
        """打开 主题 元数据文件"""
        if not self.theme_kanban:
            return
        os.startfile(self.theme_kanban.theme_metadata_file)

    def _action_delete(self) -> None:
        """删除所选 album"""
        if not self.theme_kanban:
            return
        ps = self.album_table_view.get_selected_ps()
        if not ps:
            return
        if any(self.theme_kanban.album_kanbans[p].album_res_state for p in ps):
            toast_notify("Albums with resources cannot be deleted.", 2)
            return
        if not self._ask_for_confirm("Check Again", f"Delete {len(ps)} albums?"):
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
        for p in ps:
            res_dir = self.theme_kanban.album_kanbans[p].album_dir
            os.path.exists(res_dir) and subprocess.run(f'explorer "{res_dir}"')

    def _action_search_cover(self) -> None:
        """搜索所选 album 的封面"""
        if not self.theme_kanban:
            return
        
        sources = global_settings.cover_search_engine_sources
        country = global_settings.cover_search_engine_country

        ps = self.album_table_view.get_selected_ps()
        for p in ps:
            album = self.theme_kanban.album_kanbans[p].album.album
            url = f"https://www.google.com/search?q={album}&udm=2"
            webbrowser.open(url)
            url = f"https://covers.musichoarders.xyz/?sources={sources}&country={country}&album={album}"
            webbrowser.open(url)

    def _on_paths_dropped(self, dropped_strs: list[str]) -> None:
        ps = self.album_table_view.get_selected_ps()
        # album view 至少 选中一个
        if not ps:
            return

        dropped_paths = list(map(Path, dropped_strs))
        albums = [self.theme_kanban.album_kanbans[p].album for p in ps]
        album_dirs = list(map(Path, [self.theme_kanban.album_kanbans[p].album_dir for p in ps]))

        # 选中多个 album item ，拖入多个文件夹，路径数量必须等于 album item 选中数
        if all(p.is_dir() for p in dropped_paths) and len(dropped_paths) == len(ps):
            for p, d, a in zip(dropped_paths, album_dirs, albums):
                src_files = [f for f in p.rglob("*") if f.suffix.lower() in AUDIO_EXTS]
                # 音频文件数量必须等于 tracks 数量
                if len(src_files) != len(a.tracks):
                    continue
                self._putaway_track_files(src_files, d, a)
            # 更新视图
            [self.theme_kanban.album_kanbans[p].__post_init__() for p in ps]
            self.album_table_view.viewport().update()
            return

        exts = set(p.suffix.lower() for p in dropped_paths)
        # 选中多个 album item ，拖入多个图片
        if exts.issubset(IMG_EXTS):
            # 路径数量等于 album view 选中数时
            if len(dropped_paths) == len(ps):
                [self._putaway_cover_file(*args) for args in zip(dropped_paths, album_dirs)]
            # 路径数量为一个时
            elif len(dropped_paths) == 1:
                [self._putaway_cover_file(dropped_paths[0], d) for d in album_dirs]
            # 更新视图
            [self.theme_kanban.album_kanbans[p].__post_init__() for p in ps]
            self.album_table_view.viewport().update()
            self.cover_label.set_album_kanban(self.theme_kanban.album_kanbans[ps[0]])
            return
        
        # 选中一个 album item ，选中多个 track item ，拖入多个音频文件
        if exts.issubset(AUDIO_EXTS) and len(ps) == 1:
            # 路径数量为一个时
            if len(dropped_paths) == 1:
                trackidx = self.track_table_view.selectedIndexes()[0].row()
                [self._putaway_track_file(p, d, albums[0], trackidx) for p, d in zip(dropped_paths, album_dirs)]
            # 路径数量为多个时
            else:
                self._putaway_track_files(dropped_paths, album_dirs[0], albums[0])
            self.theme_kanban.album_kanbans[ps[0]].__post_init__()
            self.album_table_view.viewport().update()
            self.track_table_view.viewport().update()

