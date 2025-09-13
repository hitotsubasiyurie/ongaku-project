import itertools
import os
import shutil
import subprocess
import random
from datetime import datetime
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QPixmap, QResizeEvent, QShortcut, QKeySequence
from PySide6.QtWidgets import (QGraphicsOpacityEffect, QGridLayout, QLabel, QLineEdit, QMessageBox, 
     QWidget, )

from src.utils import strings_assignment
from src.basemodels import Album
from src.repository_utils import track_filenames
from src.kanban.page1.widgets import (AlbumTableView, CheckMessageBox, LinkComboBox, ThemeBoxWidget, 
    TrackTableView, )
from src.kanban.kanban import AUDIO_EXTS, IMG_EXTS, KanBan, ThemeKanBan


class PageWidget1(QWidget):

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
        self.album_field.textEdited.connect(lambda t: self.album_table_view.proxy_model.set_filter(1, t))
        self.catno_field.textEdited.connect(lambda t: self.album_table_view.proxy_model.set_filter(2, t))
        self.date_field.textEdited.connect(lambda t: self.album_table_view.proxy_model.set_filter(3, t))
        self.album_table_view.selected_changed.connect(self._on_album_view_selected)
        self.album_table_view.paths_dropped.connect(self._on_paths_dropped)
        self.track_table_view.paths_dropped.connect(self._on_paths_dropped)
        self.album_table_view.action_edit_clicked.connect(self._edit_metadata_file)
        self.album_table_view.action_locate_clicked.connect(self._locate_album)

        # 拦截 album_table 和 track_table 事件
        self.album_table_view.installEventFilter(self)
        self.track_table_view.installEventFilter(self)
        self.cover_label.installEventFilter(self)

    def setup_shortcut(self) -> None:
        # 初始化 快捷键
        QShortcut(QKeySequence("Esc"), self, activated=
            lambda: [x.setText("") for x in [self.album_field, self.catno_field, self.date_field]])

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.theme_kanban: ThemeKanBan = None

        self.setup_ui()
        self.setup_event()
        self.setup_shortcut()

    def set_theme_kanban(self, theme_kanban: ThemeKanBan = None) -> None:
        self.theme_kanban = theme_kanban
        # 清空搜索框
        [x.setText("") for x in [self.album_field, self.catno_field, self.date_field]]
        self.album_table_view.source_model.set_theme_kanban(theme_kanban)
        self.album_table_view.proxy_model.unset_filter()
        self.album_table_view.proxy_model.sort(0, Qt.SortOrder.AscendingOrder)
        self.album_table_view.scrollToTop()
        self.track_table_view.source_model.set_album_kanban(None)

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
            # 任何按键释放时，透明化 cover_label
            self.cover_effect.opacity() != 0.1 and self.cover_effect.setOpacity(0.1)
            return True
        return super().eventFilter(watched, event)

    def _on_album_view_selected(self, *args, **kwargs) -> None:
        rows = list(sorted(set(i.row() for i in map(self.album_table_view.proxy_model.mapToSource, self.album_table_view.selectedIndexes()))))

        # 展示 已选 albums 的 links
        links = list(set(itertools.chain.from_iterable(self.theme_kanban.album_kanbans[r].album.links for r in rows)))
        self.link_box.set_links(links)

        # 展示 首个 album 的 track, cover
        album_kanban = self.theme_kanban.album_kanbans[rows[0]]
        self.track_table_view.source_model.set_album_kanban(album_kanban)
        if album_kanban.cover:
            pix = QPixmap(album_kanban.cover)
            pix = pix.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.cover_label.setPixmap(pix)
        else:
            self.cover_label.clear()

    def _edit_metadata_file(self) -> None:
        if self.theme_kanban:
            os.startfile(self.theme_kanban.theme_metadata_file)

    def _locate_album(self) -> None:
        # 定位 首个 album 的 资源位置
        row = self.album_table_view.proxy_model.mapToSource(self.album_table_view.selectedIndexes()[0]).row()
        res_dir = self.theme_kanban.album_kanbans[row].album_dir
        if os.path.exists(res_dir):
            subprocess.run(f'explorer "{res_dir}"')

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
        rows = list(sorted(set(i.row() for i in map(self.album_table_view.proxy_model.mapToSource, self.album_table_view.selectedIndexes()))))
        # album view 至少 选中一个
        if not rows:
            return
        albums = [self.album_table_view.model().albums[r] for r in rows]

        dropped_paths = list(map(Path, dropped_strs))
        exts = set(p.suffix.lower() for p in dropped_paths)

        dst_dirs = [self.current_theme_kanban.get_res_dir_by_album(a) for a in albums]
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
        
        self.ongaku_library.scan_all()
        self._update_album_view()

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


