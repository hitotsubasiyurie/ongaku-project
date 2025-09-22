import itertools
from typing import Any

from PySide6.QtCore import QModelIndex, Qt, QObject, Signal
from PySide6.QtGui import QAction, QBrush, QResizeEvent, QIcon
from PySide6.QtWidgets import QFrame, QWidget, QTableView, QHeaderView

from ongaku.kanban.ui_theme import current_theme
from ongaku.kanban.kanban import ThemeKanBan, ResourceState
from ongaku.kanban.widgets.custom_table_item_model import CustomTableItemModel


class PlayTableItemModel(CustomTableItemModel):

    RESOURCE_STATE_QBRUSHS = {
        ResourceState.LOSSLESS: QBrush(current_theme.LOSSLESS_COLOR),
        ResourceState.LOSSY: QBrush(current_theme.LOSSY_COLOR),
        ResourceState.MISSING: QBrush(current_theme.MISSING_COLOR),
    }

    MARKED_QBRUSHES = {
        Qt.ItemDataRole.BackgroundRole: QBrush(current_theme.MARKED_BACKGROUND_COLOR),
        Qt.ItemDataRole.ForegroundRole: QBrush(current_theme.MARKED_FOREGROUND_COLOR)
    }

    PLAYING_ICON_CACHE = None

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)

        self.headers: list[str] = ["Size", "Title", "Artist", "Album", "Date", "Mark"]
        self.col_cnt: int = len(self.headers)

        self.theme_kanban: ThemeKanBan = None

        self.tracks_states: list[ResourceState] = []
        # 看板索引
        self.kanban_index: list[tuple[int, int]] = []
        # 播放中
        self.playing_ij: tuple[int, int] = None

        # 建造 Application 后才 实例化 QIcon
        self.PLAYING_ICON_CACHE = QIcon("./kanban/assets/playing.png")

    def reset_theme_kanban(self, theme_kanban: ThemeKanBan = None) -> None:
        # 声明重置模型
        self.beginResetModel()

        # 重置数据
        self.theme_kanban = theme_kanban
        self.table = []
        self.tracks_states = []
        self.kanban_index = []
        self.playing_ij = None
        # 默认 以 Title 列 排序
        self.sort_args = (1, Qt.SortOrder.AscendingOrder)
        self.filters = {}

        # 填充数据
        if theme_kanban:
            self.tracks_states = list(itertools.chain.from_iterable(k.track_res_states for k in theme_kanban.album_kanbans))
            for i, k in enumerate(theme_kanban.album_kanbans):
                for j, t  in enumerate(k.album.tracks):
                    stat = k.track_stat_results[j]
                    size = "{:.2f} MiB".format(stat.st_size / 1024 / 1024) if stat else ""
                    self.table.append([size, t.title, t.artist, k.album.album, k.album.date, t.mark])
                    self.kanban_index.append((i, j))
    
        self.layout_ps = list(range(len(self.table)))
        # 应用排序
        self._apply_sort()
        self.layout_row = len(self.layout_ps)

        self.endResetModel()

    def data(self, index: QModelIndex, role: Qt.ItemDataRole = None) -> Any:
        row, col = index.row(), index.column()

        if not index.isValid() or row >= self.layout_row or col >= self.col_cnt:
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
        
        # Mark 列 展示 favourite
        if col == 5 and self.table[self.layout_ps[row]][5] == "1" and role in [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]:
            return "❤️"
        
        return super().data(index, role)

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole) -> Any:
        # 仅响应 DisplayRole, DecorationRole
        if role not in [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.DecorationRole]:
            return

        # 列表头 播放中 仅展示装饰图标
        if orientation == Qt.Orientation.Vertical and self.layout_ps and self.kanban_index[self.layout_ps[section]] == self.playing_ij:
            if role == Qt.ItemDataRole.DecorationRole:
                return self.PLAYING_ICON_CACHE
            else:
                return
        
        return super().headerData(section, orientation, role)
    
    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        # Size 列 不可编辑
        if index.column() == 0:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        
        return super().flags(index)

    def setData(self, index: QModelIndex, value: Any, role: Qt.ItemDataRole = Qt.ItemDataRole.EditRole) -> bool:
        row, col = index.row(), index.column()

        if not index.isValid() or row >= self.layout_row or col >= self.col_cnt:
            return False
        
        # 仅响应 EditRole
        if role != Qt.ItemDataRole.EditRole:
            return False

        # 转字符串
        value = str(value)
        p = self.layout_ps[row]

        # 值不变时不更新视图
        if self.table[p][col] == value:
            return False
        
        # 更新数据
        self.table[p][col] = value
        i, j = self.kanban_index[p]
        if col == 1:
            self.theme_kanban.album_kanbans[i].album.tracks[j].title = value
        elif col == 2:
            self.theme_kanban.album_kanbans[i].album.tracks[j].artist = value
        elif col == 3:
            self.theme_kanban.album_kanbans[i].album.album = value
        elif col == 4:
            self.theme_kanban.album_kanbans[i].album.date = value
        elif col == 5:
            self.theme_kanban.album_kanbans[i].album.tracks[j].mark = value
        
        # 刷新视图
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])
        return True


class PlayTableView(QTableView):

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
        self.item_model = PlayTableItemModel(self)
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
        # 最小列宽
        header.setMinimumSectionSize(fh*2)
        # ResizeMode
        column_modes = [QHeaderView.ResizeMode.Fixed, 
                        QHeaderView.ResizeMode.Interactive, QHeaderView.ResizeMode.Interactive, QHeaderView.ResizeMode.Interactive, 
                        QHeaderView.ResizeMode.Stretch, QHeaderView.ResizeMode.Stretch]
        [header.setSectionResizeMode(i, m) for i, m in enumerate(column_modes)]

        self.setup_context_menu()

    # 重写方法

    def resizeEvent(self, event: QResizeEvent) -> None:
        # 还原默认列宽
        fh = self.fontMetrics().height()
        column_widths = [fh*5, 0, fh*18, fh*18, fh*5, fh*2]
        [w and self.setColumnWidth(i, w) for i, w in enumerate(column_widths)]
        # Title 占据剩余宽度
        self.setColumnWidth(1, self.width() - sum(column_widths) - 1)
        return super().resizeEvent(event)



