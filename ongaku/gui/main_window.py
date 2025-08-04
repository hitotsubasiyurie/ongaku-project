import itertools
import os
import shutil
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable

import numpy
from PySide6.QtCore import (Qt, QEvent, QObject, QModelIndex, )
from PySide6.QtGui import (QPixmap, QResizeEvent, )
from PySide6.QtWidgets import (QWidget, QLineEdit, QLabel, QGridLayout, QMessageBox, QGraphicsOpacityEffect, )
from scipy.optimize import linear_sum_assignment

from ongaku.common.constants import METADATA_PATH, RESOURCE_PATH, TMP_PATH
from ongaku.common.mdf_util import (load_album, get_track_states, track_filenames, _get_album_state, album_filename)
from ongaku.common.metadata import Album
from ongaku.gui.album_table_view import AlbumTableView
from ongaku.gui.link_combo_box import LinkComboBox
from ongaku.gui.theme_box_widget import ThemeBoxWidget
from ongaku.gui.track_table_view import TrackTableView
from ongaku.gui.check_message_box import CheckMessageBox


AUDIO_EXTS = {".mp3", ".flac"}
IMG_EXTS = {".jpg", ".png"}


class MainWindow(QWidget):

    def setup_ui(self) -> None:
        self.setWindowTitle("ongaku")
        
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
        self.album_table_view.selected_changed.connect(self._set_track_view)
        self.album_table_view.paths_dropped.connect(self._on_paths_dropped)
        self.track_table_view.paths_dropped.connect(self._on_paths_dropped)
        self.album_table_view.action_edit_clicked.connect(self._edit_album)
        self.album_table_view.action_locate_clicked.connect(self._locate_album)
        self.album_table_view.action_delete_clicked.connect(self._delete_album)

        # 拦截 album_table 和 track_table 事件
        self.album_table_view.installEventFilter(self)
        self.track_table_view.installEventFilter(self)
        self.cover_label.installEventFilter(self)

    def __init__(self) -> None:
        super().__init__()

        self.metadata_dir: Path = Path(METADATA_PATH)
        self.resource_dir: Path = Path(RESOURCE_PATH)
        self.tmp_dir: Path = Path(TMP_PATH)

        self.setup_ui()
        self.setup_event()

        self._refresh_album_view()

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
                self._refresh_album_view()
            # 其余按键释放时，透明化 cover_label
            else:
                self.cover_effect.setOpacity(0.1)
            return True
        return super().eventFilter(watched, event)

    # 内部方法

    def _refresh_album_view(self) -> None:
        self._scan_metadata_dir()
        self._scan_resource_dir()
        self._set_album_view()
        # 聚焦 album view 、索引第一行
        self.album_table_view.setFocus()
        self.album_table_view.selectRow(0)
        self.album_table_view.setCurrentIndex(self.album_table_view.selectedIndexes()[0])

    def _scan_metadata_dir(self) -> None:
        self.album_mdfs = list(self.metadata_dir.rglob("*.json"))
        self.albums = list(map(load_album, self.album_mdfs))
        self.aid2idx = {id(a): i for i, a in enumerate(self.albums)}

    def _scan_resource_dir(self) -> None:
        _dname2path = {p.name: p for p in self.resource_dir.rglob("*") if p.is_dir()}
        self.album_dirs = [_dname2path.get(f.stem, None) for f in self.album_mdfs]
        self.track_states = [get_track_states(a, d) for a, d in zip(self.albums, self.album_dirs)]
        self.album_states = list(map(_get_album_state, self.track_states))
        self.album_imgs = [d and next((p for p in Path(d).rglob("*") if p.name.lower() in ["cover.jpg", "cover.png"]), None)
                            for d in self.album_dirs]

    def _set_album_view(self, *args, **kwargs) -> None:
        # 筛选
        album_key = self.album_field.text().lower()
        catno_key = self.catno_field.text().lower()
        date_key = self.date_field.text().lower()
        themes_key = set(self.theme_field.selected)

        tmp = [(a, s) for a, s in zip(self.albums, self.album_states)
               if album_key in a.album.lower() and catno_key in a.catalognumber.lower() \
               and date_key in a.date.lower() and themes_key.issubset(a.themes)]
        
        albums, album_states = list(zip(*tmp)) if tmp else [[], []]
        self.album_table_view.set_albums(albums, album_states)
        self.theme_field.set_themes(list(set(itertools.chain.from_iterable(a.themes for a in albums))))

    def _set_track_view(self, *args, **kwargs) -> None:
        rows = [i.row() for i in self.album_table_view.selectedIndexes()]
        albums = [self.album_table_view.model().albums[r] for r in rows]
        idxs = [self.aid2idx[id(a)] for a in albums]

        # 多选 albums 的 links, themes
        self.link_box.set_links(list(set(itertools.chain.from_iterable(a.links for a in albums))))
        self.theme_field.set_current_themes(list(set(itertools.chain.from_iterable(a.themes for a in albums))))

        # 首个 album 的 track, cover
        self.track_table_view.set_tracks(albums[0].tracks, self.track_states[idxs[0]])
        if img:= self.album_imgs[idxs[0]]:
            pix = QPixmap(img)
            pix = pix.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.cover_label.setPixmap(pix)
        else:
            self.cover_label.clear()

    def _locate_album(self) -> None:
        """打开 album 资源所在文件夹"""
        a_row = self.album_table_view.selectedIndexes()[0].row()
        album = self.album_table_view.model().albums[a_row]
        idx = self.aid2idx[id(album)]
        album_dir = self.album_dirs[idx]
        album_dir and os.startfile(album_dir)

    def _edit_album(self) -> None:
        """编辑 album 元数据文件"""
        a_row = self.album_table_view.selectedIndexes()[0].row()
        album = self.album_table_view.model().albums[a_row]
        idx = self.aid2idx[id(album)]
        mdf = self.album_mdfs[idx]
        os.startfile(mdf)

    def _delete_album(self) -> None:
        """删除 album 元数据文件"""
        rows = list(sorted(set(i.row() for i in self.album_table_view.selectedIndexes())))
        albums = [self.album_table_view.model().albums[r] for r in rows]
        idxs = [self.aid2idx[id(a)] for a in albums]
        if not rows:
            return
        mdfs = [self.album_mdfs[idx] for idx in idxs]

        def _operate() -> None:
            [f.unlink() for f in mdfs]
            # 刷新视图
            self._refresh_album_view()
        
        text = "Will delete files:\n\n" + "\n".join(map(str, mdfs))
        self._show_check_message("Check Again", text, icon=QMessageBox.Icon.Warning, on_yes_clicked=_operate)

    def _show_check_message(self, title: str, text: str, icon: QMessageBox.Icon = None, on_yes_clicked: Callable = None, 
                            on_no_clicked: Callable = None) -> None:
        """弹出确认对话框"""
        check_msg = CheckMessageBox(parent=self)
        check_msg.setText(text)
        check_msg.setWindowTitle(title)
        icon and check_msg.setIcon(icon)

        check_msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        # 设置默认按钮为 NO
        check_msg.setDefaultButton(QMessageBox.StandardButton.No)
        on_yes_clicked and check_msg.button(QMessageBox.StandardButton.Yes).clicked.connect(on_yes_clicked)
        on_no_clicked and check_msg.button(QMessageBox.StandardButton.No).clicked.connect(on_no_clicked)
        check_msg.show()

    def _on_paths_dropped(self, given_strs: list[str]) -> None:
        # selectedIndexes 以索引为单位，一行多个
        rows = list(sorted(set(i.row() for i in self.album_table_view.selectedIndexes())))
        # album view 至少 选中一个
        if not rows:
            return
        albums = [self.album_table_view.model().albums[r] for r in rows]
        idxs = [self.aid2idx[id(a)] for a in albums]

        dst_dirs = [self.album_dirs[idx] or self.resource_dir/self.album_mdfs[idx].stem 
                    for idx in idxs]
        [d.mkdir(exist_ok=True) for d in dst_dirs]

        given_paths = list(map(Path, given_strs))

        # 拖入文件夹列表时
        if all(p.is_dir() for p in given_paths):
            # 数量等于 album view 选中数
            if len(given_paths) == len(albums):
                [self._on_album_src_dropped(*args) for args in zip(given_paths, dst_dirs, albums)]
            return

        exts = set(p.suffix.lower() for p in given_paths)
        # 拖入图片列表时
        if exts.issubset(IMG_EXTS):
            # 数量等于 album view 选中数
            if len(given_paths) == len(albums):
                [self._on_cover_src_dropped(*args) for args in zip(given_paths, dst_dirs)]
            # 数量为一个
            elif len(given_paths) == 1:
                [self._on_cover_src_dropped(given_paths[0], d) for d in dst_dirs]

        # 拖入音频列表时，album view 选中一个
        elif exts.issubset(AUDIO_EXTS) and len(albums) == 1:
            # 拖入数量为一个
            if len(given_paths) == 1:
                trackidx = self.track_table_view.selectedIndexes()[0].row()
                [self._on_track_src_dropped(p, d, albums[0], trackidx) for p, d in zip(given_paths, dst_dirs)]
            else:
                self._on_album_src_dropped(given_paths, dst_dirs[0], albums[0])

    def _on_album_src_dropped(self, given_path: Path | list[Path], dst_dir: Path, album: Album) -> None:
        src_files = given_path if isinstance(given_path, list) else \
            [p for p in given_path.rglob("*") if p.suffix.lower() in AUDIO_EXTS]
        
        # 轨道数量相等
        if len(album.tracks) != len(src_files):
            return
        dst_files = [dst_dir / (n+f.suffix) for f, n in zip(src_files, track_filenames(album))]
        
        # 一一配对 总相似度最高
        k = len(album.tracks)
        sim_matrix = [[SequenceMatcher(None, src_files[n].stem, dst_files[m].stem).ratio() for m in range(k)] 
                        for n in range(k)]
        sim_matrix = numpy.asarray(sim_matrix)
        row_ind, col_ind = linear_sum_assignment(sim_matrix, maximize=True)
        _map: dict[Path, Path] = {src_files[row_ind[n]]: dst_files[col_ind[n]] for n in range(k)}
        aver_similarity = sim_matrix[row_ind, col_ind].sum() / k

        def _operate() -> None:
            [src.rename(dst) for src, dst in _map.items()]

            if isinstance(given_path, list):
                return

            imgs = [p for p in given_path.rglob("*") if p.suffix.lower() in IMG_EXTS]
            cover = None
            # 唯一的图片，或名字为 cover ，认为是封面
            cover = imgs[0] if len(imgs) == 1 else next((p for p in imgs if p.stem.lower()=="cover"), None)
            cover and self._on_cover_src_dropped(cover, dst_dir)

        text = (f"{None if isinstance(given_path, list) else given_path.name}\n\n{album.album}\n\nAverage Similarity: {aver_similarity:.02f}\n\n"
                + "\n".join(f"      {k.name}\n->  {v.name}\n" for k, v in _map.items()))
        self._show_check_message("Check Again", text, on_yes_clicked=_operate)

    def _on_cover_src_dropped(self, given_path: Path, dst_dir: Path) -> None:
        ext = given_path.suffix.lower()
        src, dst = given_path, dst_dir / ("cover"+ext)
        shutil.copy2(src, dst)

    def _on_track_src_dropped(self, given_path: Path, dst_dir: Path, album: Album, trackidx: int) -> None:
        ext = given_path.suffix.lower()
        src, dst = given_path, dst_dir / (track_filenames(album)[trackidx]+ext)

        def _operate() -> None:
            src.rename(dst)

        text = f"      {src.name}\n->  {dst.name}"
        self._show_check_message("Check Again", text, on_yes_clicked=_operate)

