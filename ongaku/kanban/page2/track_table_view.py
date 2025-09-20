import re
import itertools
from typing import Any

from PySide6.QtCore import QModelIndex, Qt, QObject, Signal
from PySide6.QtGui import QAction, QBrush
from PySide6.QtWidgets import QFrame, QWidget, QTableView, QHeaderView

from ongaku.kanban.theme_colors import current_theme
from ongaku.kanban.kanban import ThemeKanBan, ResourceState
from ongaku.kanban.custom_table_item_model import CustomTableItemModel


class TrackTableItemModel(CustomTableItemModel):

    RESOURCE_STATE_QBRUSHS = {
        ResourceState.LOSSLESS: QBrush(current_theme.LOSSLESS_COLOR),
        ResourceState.LOSSY: QBrush(current_theme.LOSSY_COLOR),
        ResourceState.MISSING: QBrush(current_theme.MISSING_COLOR),
    }

    MARKED_QBRUSHES = {
        Qt.ItemDataRole.BackgroundRole: QBrush(current_theme.MARKED_BACKGROUND_COLOR),
        Qt.ItemDataRole.ForegroundRole: QBrush(current_theme.MARKED_FOREGROUND_COLOR)
    }

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)

        self.headers: list[str] = ["Size", "Title", "Artist", "Album", "Date", "Mark"]
        self.col_cnt: int = len(self.headers)

        self.tracks_states: list[ResourceState] = []
        # 原始索引
        self.original_index: list[tuple[int, int]] = []

    def set_theme_kanban(self, theme_kanban: ThemeKanBan = None) -> None:
        # 声明重置模型
        self.beginResetModel()

        # 重置数据
        self.table = []
        self.original_index = []
        self.tracks_states = []
        # 默认 以 Title 列 排序
        self.sort_args = (1, Qt.SortOrder.AscendingOrder)
        self.filters = {}

        if theme_kanban:
            self.tracks_states = list(itertools.chain.from_iterable(k.track_res_states for k in theme_kanban.album_kanbans))
            for i, k in enumerate(theme_kanban.album_kanbans):
                for j, t  in enumerate(k.album.tracks):
                    stat = k.track_stat_results[j]
                    size = "{:.2f} MiB".format(stat.st_size / 1024 / 1024) if stat else ""
                    self.table.append([size, t.title, t.artist, k.album.album, k.album.date, t.mark])
                    self.original_index.append((i, j))
    
        self.layout_ps = list(range(len(self.table)))
        # 应用排序
        self._apply_sort()
        self.row_cnt = len(self.layout_ps)

        self.endResetModel()

    def data(self, index: QModelIndex, role: Qt.ItemDataRole = None) -> Any:
        row, col = index.row(), index.column()

        if not index.isValid() or row >= self.row_cnt or col >= self.col_cnt:
            return None
        
        # Size 列 资源状态 字体颜色
        if col == 0 and role == Qt.ItemDataRole.ForegroundRole:
            return self.RESOURCE_STATE_QBRUSHS[self.tracks_states[self.layout_ps[row]]]
        
        # Size 列 文本右对齐
        if col in [0] and role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignRight
        # Date, Mark 列 文本居中
        if col in [4, 5] and role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignCenter
        
        # 已有 Mark 信息 置灰
        if self.table[self.layout_ps[row]][5] and role in self.MARKED_QBRUSHES:
            return self.MARKED_QBRUSHES[role]
        
        if col == 5 and self.table[self.layout_ps[row]][5] == "1" and role in [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]:
            return "❤️"
        
        return super().data(index, role)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        # Size 列 只可点击
        if index.column() == 0:
            return Qt.ItemFlag.ItemIsEnabled
        
        return super().flags(index)


class TrackTableView(QTableView):

    favourite_selected = Signal()
    unfavourite_selected = Signal()
    clear_selected = Signal()

    def setup_context_menu(self) -> None:
        # 初始化 右键菜单
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        action = QAction("♡ Listened", self)
        action.triggered.connect(self.unfavourite_selected.emit)
        self.addAction(action)
        action = QAction("❤ Favourite", self)
        action.triggered.connect(self.favourite_selected.emit)
        self.addAction(action)
        action = QAction("Clear Mark", self)
        action.triggered.connect(self.clear_selected.emit)
        self.addAction(action)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        # 设置模型
        self.item_model = TrackTableItemModel(self)
        self.setModel(self.item_model)
        # 重置、排序、筛选 后 滚动至开头
        self.item_model.layoutChanged.connect(self.scrollToTop)

        # 表格无边框
        self.setShowGrid(False)
        self.setFrameShape(QFrame.Shape.NoFrame)
        # 可编辑
        self.setEditTriggers(QTableView.EditTrigger.DoubleClicked)
        # 多选
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        # 可排序
        self.setSortingEnabled(True)
        # 条目滚动 提高性能
        self.setVerticalScrollMode(QTableView.ScrollMode.ScrollPerItem)
        # 隐藏滚动条
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 字体高度
        fh = self.fontMetrics().height()

        # 设置行
        header = self.verticalHeader()
        header.setDefaultSectionSize(fh)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header.setSectionsClickable(False)
        header.setFrameShape(QFrame.Shape.NoFrame)

        # 设置 列
        header = self.horizontalHeader()
        column_widths = [fh*5, 0, fh*18, fh*18, fh*5, fh*2]
        [self.setColumnWidth(i, w) for i, w in enumerate(column_widths)]
        column_modes = [QHeaderView.ResizeMode.Fixed if w else QHeaderView.ResizeMode.Stretch for w in column_widths]
        [header.setSectionResizeMode(i, m) for i, m in enumerate(column_modes)]

        self.setup_context_menu()

















