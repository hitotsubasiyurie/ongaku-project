import itertools
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QPixmap, QResizeEvent
from PySide6.QtWidgets import (QGraphicsOpacityEffect, QGridLayout, QLabel, QLineEdit, QMessageBox, 
    QWidget, )

from src.gui.album_table_view import AlbumTableView
from src.gui.check_message_box import CheckMessageBox
from src.gui.link_combo_box import LinkComboBox
from src.gui.theme_box_widget import ThemeBoxWidget
from src.gui.track_table_view import TrackTableView
from src.common.utils import strings_assignment
from src.ongaku_library.basemodels import Album
from src.ongaku_library.ongaku_library import AUDIO_EXTS, IMG_EXTS, OngakuLibrary, track_filenames


class MainWindow(QWidget):

    def setup_ui(self) -> None:
        self.setWindowTitle("OngakuKanban")
        
        # 初始化 UI
        grid_layout = QGridLayout()
        self.setLayout(grid_layout)

        self.album_field = QLineEdit()
        grid_layout.addWidget(self.album_field, 0, 0, 1, 1)

        self.catno_field = QLineEdit()
        grid_layout.addWidget(self.catno_field, 0, 1, 1, 1)

        self.date_field = QLineEdit()
        grid_layout.addWidget(self.date_field, 0, 2, 1, 1)

        self.link_box = LinkComboBox()
        grid_layout.addWidget(self.link_box, 0, 3, 1, 1)

        self.theme_field = ThemeBoxWidget()
        grid_layout.addWidget(self.theme_field, 0, 4, 1, 1)

        self.album_table_view = AlbumTableView()
        grid_layout.addWidget(self.album_table_view, 1, 0, 2, 3)

        self.track_table_view = TrackTableView()
        grid_layout.addWidget(self.track_table_view, 1, 3, 1, 2)

        col_stretch = [5, 1, 1, 2, 4]
        [s and grid_layout.setColumnStretch(i, s) for i, s in enumerate(col_stretch)]

        self.cover_label = QLabel(self)
        # 鼠标事件透传
        self.cover_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.cover_label.raise_()
        # 透明度
        self.cover_effect = QGraphicsOpacityEffect(self)
        self.cover_effect.setOpacity(0.1)
        self.cover_label.setGraphicsEffect(self.cover_effect)
        # 对齐
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def setup_event(self) -> None:
        # 初始化 事件
        self.album_field.textEdited.connect(self._set_album_view)
        self.catno_field.textEdited.connect(self._set_album_view)
        self.date_field.textEdited.connect(self._set_album_view)
        self.theme_field.selected_changed.connect(self._set_album_view)
        self.album_table_view.selected_changed.connect(self._on_album_view_selected)
        self.album_table_view.paths_dropped.connect(self._on_paths_dropped)
        self.track_table_view.paths_dropped.connect(self._on_paths_dropped)
        self.album_table_view.action_edit_clicked.connect(self._edit_album)
        self.album_table_view.action_locate_clicked.connect(self._locate_album)
        self.album_table_view.action_group_clicked.connect(self._group_album)

        # 拦截 album_table 和 track_table 事件
        self.album_table_view.installEventFilter(self)
        self.track_table_view.installEventFilter(self)
        self.cover_label.installEventFilter(self)

    def __init__(self, metadata_dir: str, resource_dir: str) -> None:
        super().__init__()

        self.ongaku_library = OngakuLibrary(metadata_dir, resource_dir)

        self.setup_ui()
        self.setup_event()

        self._set_album_view()

    # 重写方法

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.cover_label.resize(self.size())

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress:
            # 英文状态下 ~ 键按下时，非透明展示 cover_label
            if event.key() == Qt.Key.Key_QuoteLeft:
                self.cover_effect.setOpacity(1)
                return True
            # 上下键按下时，传递给子控件
            if event.key() in [Qt.Key.Key_Up, Qt.Key.Key_Down]:
                return False
            # 其余键按下时，拦截
            return True
        if event.type() == QEvent.Type.KeyRelease:
            # F5 键释放时，刷新视图
            if event.key() == Qt.Key.Key_F5:
                self.ongaku_library._scan_all()
                self._set_album_view()
            # 任何按键释放时，透明化 cover_label
            self.cover_effect.opacity() != 0.1 and self.cover_effect.setOpacity(0.1)
            return True
        return super().eventFilter(watched, event)

    def _set_album_view(self, *args, **kwargs) -> None:
        # 根据 搜索框 过滤 albums
        album_key = self.album_field.text().lower()
        catno_key = self.catno_field.text().lower()
        date_key = self.date_field.text().lower()
        themes_key = self.theme_field.selected

        albums = self.ongaku_library.get_albums()
        metadata_states = self.ongaku_library.get_album_metadata_states()
        resource_states = self.ongaku_library.get_album_resource_states()

        tmp = [(a, ms, rs) for a, ms, rs in zip(albums, metadata_states, resource_states)
               if album_key in a.album.lower() and catno_key in a.catalognumber.lower() \
               and date_key in a.date.lower() and themes_key.issubset(a.themes)]
        
        albums, metadata_states, resource_states = list(zip(*tmp)) if tmp else [[], [], []]
        self.album_table_view.set_albums(albums, metadata_states, resource_states)
        # 设置 theme view
        themes = set(itertools.chain.from_iterable(a.themes for a in albums))
        completions = self.ongaku_library.get_theme_completions()
        self.theme_field.set_themes(themes, completions)

    def _on_album_view_selected(self, *args, **kwargs) -> None:
        rows = list(sorted(set(i.row() for i in self.album_table_view.selectedIndexes())))
        albums = [self.album_table_view.model().albums[r] for r in rows]

        # 展示 已选 albums 的 links, themes
        self.link_box.set_links(list(set(itertools.chain.from_iterable(a.links for a in albums))))
        self.theme_field.set_indicate_themes(set(itertools.chain.from_iterable(a.themes for a in albums)))

        # 展示 首个 album 的 track, cover
        a = albums[0]
        self.track_table_view.set_tracks(a.tracks, self.ongaku_library.get_album_track_states(a))
        if cover:= self.ongaku_library.get_album_covers(a):
            pix = QPixmap(cover)
            pix = pix.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.cover_label.setPixmap(pix)
        else:
            self.cover_label.clear()

    def _locate_album(self) -> None:
        # 定位 首个 album 的 资源位置
        row = self.album_table_view.selectedIndexes()[0].row()
        a = self.album_table_view.model().albums[row]
        if res_dir:= self.ongaku_library.get_album_resource_dirs(a):
            subprocess.run(f'explorer /select, "{res_dir}"')

    def _edit_album(self) -> None:
        # 编辑 首个 album 元数据文件
        row = self.album_table_view.selectedIndexes()[0].row()
        a = self.album_table_view.model().albums[row]
        mdf = self.ongaku_library.get_album_metadata_files(a)
        os.startfile(mdf)

    def _group_album(self) -> None:
        rows = list(sorted(set(i.row() for i in self.album_table_view.selectedIndexes())))
        if not rows:
            return
        albums = [self.album_table_view.model().albums[r] for r in rows]
        mdfs  = list(map(self.ongaku_library.get_album_metadata_files, albums))
        group = Path(self.ongaku_library.metadata_dir, datetime.now().strftime("%Y%m%d%H%M%S"))
        group.mkdir()
        [os.symlink(f, group / os.path.basename(f)) for f in mdfs]

    def _show_check_message(self, title: str, text: str, on_yes_clicked: Callable = None, 
                            on_no_clicked: Callable = None) -> bool:
        """弹出确认对话框"""
        check_msg = CheckMessageBox(title, text, parent=self)
        check_msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        # 设置默认按钮为 NO
        check_msg.setDefaultButton(QMessageBox.StandardButton.No)
        on_yes_clicked and check_msg.button(QMessageBox.StandardButton.Yes).clicked.connect(on_yes_clicked)
        on_no_clicked and check_msg.button(QMessageBox.StandardButton.No).clicked.connect(on_no_clicked)
        # 阻塞
        accept = check_msg.exec() == QMessageBox.StandardButton.Yes
        return accept 

    def _on_paths_dropped(self, dropped_strs: list[str]) -> None:
        # selectedIndexes 以索引为单位，一行多个
        rows = list(sorted(set(i.row() for i in self.album_table_view.selectedIndexes())))
        # album view 至少 选中一个
        if not rows:
            return
        albums = [self.album_table_view.model().albums[r] for r in rows]

        dropped_paths = list(map(Path, dropped_strs))
        exts = set(p.suffix.lower() for p in dropped_paths)

        dst_dirs = [self.ongaku_library.get_album_resource_dirs(a) 
                    or self.ongaku_library.get_album_dst_resource_dirs(a)
                    for a in albums]
        dst_dirs = list(map(Path, dst_dirs))

        # 拖入文件夹列表时
        if all(p.is_dir() for p in dropped_paths):
            # 路径数量必须等于 album view 选中数
            if len(dropped_paths) != len(albums):
                return
            for p, d, a in zip(dropped_paths, dst_dirs, albums):
                src_files = [f for f in p.rglob("*") if f.suffix.lower() in AUDIO_EXTS]
                # 音频文件数量必须等于 tracks 数量
                if len(src_files) != len(a.tracks):
                    continue
                result = self._putaway_track_files(src_files, d, a)
                if not result:
                    continue
                # 存库音轨成功后 再存库封面
                imgs = [i for i in p.rglob("*") if i.suffix.lower() in IMG_EXTS]
                cover = None
                # 唯一的图片，或名字为 cover ，认为是封面
                cover = imgs[0] if len(imgs) == 1 else next((i for i in imgs if i.stem.lower()=="cover"), None)
                cover and self._putaway_cover_file(cover, d)
        # 拖入图片列表时
        elif exts.issubset(IMG_EXTS):
            # 路径数量等于 album view 选中数
            if len(dropped_paths) == len(albums):
                [self._putaway_cover_file(*args) for args in zip(dropped_paths, dst_dirs)]
            # 路径数量为一个
            elif len(dropped_paths) == 1:
                [self._putaway_cover_file(dropped_paths[0], d) for d in dst_dirs]
            else:
                return
        # 拖入音频列表时
        elif exts.issubset(AUDIO_EXTS):
            # album view 必须仅选中一个
            if len(albums) != 1:
                return
            # 路径数量为一个
            if len(dropped_paths) == 1:
                trackidx = self.track_table_view.selectedIndexes()[0].row()
                [self._putaway_track_file(p, d, albums[0], trackidx) for p, d in zip(dropped_paths, dst_dirs)]
            # 路径数量为多个
            else:
                self._putaway_track_files(dropped_paths, dst_dirs[0], albums[0])
        
        self.ongaku_library._scan_all()
        self._set_album_view()

    def _putaway_cover_file(self, src: Path, dst_dir: Path) -> bool:
        # TODO: 已存在封面时，是否覆盖
        dst_dir.mkdir(parents=True, exist_ok=True)
        ext = src.suffix.lower()
        dst = dst_dir / ("cover"+ext)
        shutil.copy2(src, dst)
        return True

    def _putaway_track_file(self, src: Path, dst_dir: Path, album: Album, trackidx: int) -> bool:
        dst_dir.mkdir(parents=True, exist_ok=True)
        ext = src.suffix.lower()
        dst = dst_dir / (track_filenames(album)[trackidx]+ext)

        text = f"      {src.name}\n->  {dst.name}"
        accept = self._show_check_message("Check Again", text)

        if not accept:
            return False
        
        src.rename(dst)
        return True

    def _putaway_track_files(self, src_files: list[Path], dst_dir: Path, album: Album) -> bool:
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst_files = [dst_dir / (n+f.suffix) for f, n in zip(src_files, track_filenames(album))]
        
        aver_similarity, row_ind, col_ind = strings_assignment([f.stem for f in src_files], [f.stem for f in dst_files])
        _map: dict[Path, Path] = {src_files[row]: dst_files[col] for row, col in zip(row_ind, col_ind)}
        text = f"Directory:\t{src_files[0].parent.name}\nAlbum:\t\t{album.album}\nAverage Similarity:\t{aver_similarity:.02f}\n\n"
        text += "\n".join(f"      {k.name}\n->  {v.name}\n" for k, v in _map.items())
        accept = self._show_check_message("Check Again", text)
        
        if not accept:
            return False
        
        [src.rename(dst) for src, dst in _map.items()]
        return True


