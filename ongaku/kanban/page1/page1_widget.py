import os
import shutil
import subprocess
import itertools
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QPixmap, QResizeEvent, QShortcut, QKeySequence
from PySide6.QtWidgets import (QGraphicsOpacityEffect, QGridLayout, QLabel, QLineEdit, QMessageBox, 
     QWidget, )

from ongaku.core.basemodels import Album
from ongaku.core.constants import AUDIO_EXTS, IMG_EXTS
from ongaku.utils.audiofile_utils import analyze_resource_track
from ongaku.utils.storage_utils import track_filenames
from ongaku.utils.basemodel_utils import tracks_assignment, track_to_unique_str
from ongaku.kanban.kanban import ThemeKanBan
from ongaku.kanban.page1.album_table_view import AlbumTableView
from ongaku.kanban.page1.check_message_box import CheckMessageBox
from ongaku.kanban.page1.link_combo_box import LinkComboBox
from ongaku.kanban.page1.track_table_view import TrackTableView


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

        self.cover_label = QLabel(self)
        # 鼠标事件透传
        self.cover_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.cover_label.raise_()
        # 透明度
        self.cover_effect = QGraphicsOpacityEffect(self)
        self.cover_effect.setOpacity(0.2)
        self.cover_label.setGraphicsEffect(self.cover_effect)
        # 对齐
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def setup_event(self) -> None:
        # 初始化 事件
        # 搜索框
        self.album_field.textChanged.connect(lambda t: self.album_table_view.item_model.set_filter(1, t))
        self.catno_field.textChanged.connect(lambda t: self.album_table_view.item_model.set_filter(2, t))
        self.date_field.textChanged.connect(lambda t: self.album_table_view.item_model.set_filter(3, t))
        self.album_table_view.selectionModel().selectionChanged.connect(self._on_album_view_selected)
        # view 拖入路径
        self.album_table_view.paths_dropped.connect(self._on_paths_dropped)
        self.track_table_view.paths_dropped.connect(self._on_paths_dropped)
        # album_table_view 右键菜单动作
        self.album_table_view.action_edit_clicked.connect(self._edit_metadata_file)
        self.album_table_view.action_locate_clicked.connect(self._locate_album)
        # view 编辑数据
        self.track_table_view.item_model.dataChanged.connect(lambda: self.theme_kanban.save_metadata_file())
        self.album_table_view.item_model.dataChanged.connect(lambda: self.theme_kanban.save_metadata_file())

        # 拦截 album_table 和 track_table 事件
        self.album_table_view.installEventFilter(self)
        self.track_table_view.installEventFilter(self)
        self.cover_label.installEventFilter(self)

    def setup_shortcut(self) -> None:
        # 初始化 快捷键
        QShortcut(QKeySequence("Esc"), self, activated=
            lambda: [x.clear() for x in [self.album_field, self.catno_field, self.date_field]])

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.theme_kanban: ThemeKanBan = None

        self.setup_ui()
        self.setup_event()
        self.setup_shortcut()

    def set_theme_kanban(self, theme_kanban: ThemeKanBan = None) -> None:
        self.theme_kanban = theme_kanban
        # 清空搜索框
        [x.clear() for x in [self.album_field, self.catno_field, self.date_field]]
        self.cover_label.clear()
        self.album_table_view.item_model.reset_theme_kanban(theme_kanban)
        self.track_table_view.item_model.reset_album_kanban(None)

    # 重写方法

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.cover_label.resize(self.size())

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() not in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            return super().eventFilter(watched, event)

        key = event.key()

        #  ~ 键控制 cover_label 展示
        if key == Qt.Key.Key_QuoteLeft:
            if event.type() == QEvent.Type.KeyPress:
                self.cover_effect.setOpacity(1)
            elif event.type() == QEvent.Type.KeyRelease:
                self.cover_effect.setOpacity(0.2)
            return True

        # 放行上下键
        if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            return False

        # 拦截其他按键
        return True

    def _on_album_view_selected(self, *args, **kwargs) -> None:
        rows = list(sorted(set(i.row() for i in self.album_table_view.selectedIndexes())))
        if not rows:
            return
        # 原始数据行指针
        ps = [self.album_table_view.item_model.layout_ps[r] for r in rows]

        # 展示 所有已选 albums 的 links
        links = list(set(itertools.chain.from_iterable(self.theme_kanban.album_kanbans[p].album.links for p in ps)))
        self.link_box.set_links(links)

        # 展示 首个 album 的 track, cover
        album_kanban = self.theme_kanban.album_kanbans[ps[0]]
        self.track_table_view.item_model.reset_album_kanban(album_kanban)
        if album_kanban.cover:
            pix = QPixmap(album_kanban.cover)
            pix = pix.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.cover_label.setPixmap(pix)
        else:
            self.cover_label.clear()

    def _edit_metadata_file(self) -> None:
        # 打开 元数据文件
        if self.theme_kanban:
            os.startfile(self.theme_kanban.theme_metadata_file)

    def _locate_album(self) -> None:
        # 打开 首个 album 的 资源位置
        rows = list(sorted(set(i.row() for i in self.album_table_view.selectedIndexes())))
        if not rows or not self.theme_kanban:
            return
        p = self.album_table_view.item_model.layout_ps[rows[0]]
        res_dir = self.theme_kanban.album_kanbans[p].album_dir
        if os.path.exists(res_dir):
            subprocess.run(f'explorer "{res_dir}"')

    def _on_paths_dropped(self, dropped_strs: list[str]) -> None:
        # selectedIndexes 以索引为单位，一行多个
        rows = list(sorted(set(i.row() for i in self.album_table_view.selectedIndexes())))
        # album view 至少 选中一个
        if not rows:
            return

        # 原始数据行指针
        ps = [self.album_table_view.item_model.layout_ps[r] for r in rows]

        dropped_paths = list(map(Path, dropped_strs))
        albums = [self.theme_kanban.album_kanbans[p].album for p in ps]
        album_dirs = list(map(Path, [self.theme_kanban.album_kanbans[p].album_dir for p in ps]))

        # 选中多个 album item ，拖入多个文件夹，路径数量必须等于 album item 选中数
        if all(p.is_dir() for p in dropped_paths) and len(dropped_paths) == len(albums):
            for p, d, a in zip(dropped_paths, album_dirs, albums):
                src_files = [f for f in p.rglob("*") if f.suffix.lower() in AUDIO_EXTS]
                # 音频文件数量必须等于 tracks 数量
                if len(src_files) != len(a.tracks):
                    continue
                self._putaway_track_files(src_files, d, a)
            # 更新视图
            # TODO: kanban 和 model 之间隔了一层 table 缓存
            # 怎么简便的更新呢？
            [self.theme_kanban.album_kanbans[p].__post_init__() for p in ps]
            return
        
        exts = set(p.suffix.lower() for p in dropped_paths)
        # 选中多个 album item ，拖入多个图片
        if exts.issubset(IMG_EXTS):
            # 路径数量等于 album view 选中数时
            if len(dropped_paths) == len(albums):
                [self._putaway_cover_file(*args) for args in zip(dropped_paths, album_dirs)]
            # 路径数量为一个时
            elif len(dropped_paths) == 1:
                [self._putaway_cover_file(dropped_paths[0], d) for d in album_dirs]
            return
        # 选中一个 album item ，选中多个 track item ，拖入多个音频文件
        if exts.issubset(AUDIO_EXTS) and len(albums) == 1:
            # 路径数量为一个时
            if len(dropped_paths) == 1:
                trackidx = self.track_table_view.selectedIndexes()[0].row()
                [self._putaway_track_file(p, d, albums[0], trackidx) for p, d in zip(dropped_paths, album_dirs)]
            # 路径数量为多个时
            else:
                self._putaway_track_files(dropped_paths, album_dirs[0], albums[0])
        
        # TODO: 更新？
        self.theme_kanban.scan()
        self.set_theme_kanban(self.theme_kanban)

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
        accept = self._show_check_message("Check Again", text)
        
        if not accept:
            return False
        
        [src.rename(dst) for src, dst in _map.items()]
        return True

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

