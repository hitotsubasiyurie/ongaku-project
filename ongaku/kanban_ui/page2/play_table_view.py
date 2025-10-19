import re
from typing import Any

from PySide6.QtCore import QModelIndex, Qt, QObject, Signal
from PySide6.QtGui import QAction, QBrush, QResizeEvent, QIcon
from PySide6.QtWidgets import QFrame, QWidget, QTableView, QHeaderView

from ongaku.core.kanban import ThemeKanBan, ResourceState
from ongaku.kanban_ui.color_theme import current_theme
from ongaku.kanban_ui.custom.custom_table_item_model import CustomTableItemModel


class PlayTableItemModel(CustomTableItemModel):

    RESOURCE_STATE_QBRUSHS = {
        ResourceState.LOSSLESS: QBrush(current_theme.LOSSLESS_COLOR),
        ResourceState.LOSSY: QBrush(current_theme.LOSSY_COLOR),
        ResourceState.MISSING: QBrush(current_theme.MISSING_COLOR),
    }

    MARKED_BACKGROUND_QBRUSHES = QBrush(current_theme.MARKED_BACKGROUND_COLOR)
    MARKED_FOREGROUND_QBRUSHES = QBrush(current_theme.MARKED_FOREGROUND_COLOR)

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)

        self.headers = ["Size", "Title", "Artist", "Album", "Date", "Mark"]

        self.theme_kanban: ThemeKanBan = None

        # 看板索引
        self.kanban_ij: list[tuple[int, int]] = []
        # 播放中索引
        self.playing_ij: tuple[int, int] = None

    def reset_theme_kanban(self, theme_kanban: ThemeKanBan = None) -> None:
        # 声明重置模型
        self.beginResetModel()

        # 重置数据
        self.theme_kanban = theme_kanban
        self.kanban_ij = [(i, j) 
                          for i, ak in enumerate(theme_kanban.album_kanbans)
                          for j, t in enumerate(ak.album.tracks)] if theme_kanban else []
        self.playing_ij = None
        self.layout_ps = list(range(len(self.kanban_ij))) if theme_kanban else []

        # 默认 以 Title 列 排序
        self.sort_args = (1, Qt.SortOrder.AscendingOrder)
        # 清空筛选
        self.filters = {}

        # 应用排序
        self._apply_sort()

        self.endResetModel()

    def data(self, index: QModelIndex, role: Qt.ItemDataRole = None) -> Any:
        row, col = index.row(), index.column()

        if not index.isValid() or row >= len(self.layout_ps) or col >= len(self.headers):
            return None

        i, j = self.kanban_ij[self.layout_ps[row]]

        # 前景
        if role == Qt.ItemDataRole.ForegroundRole:
            # Size 列 资源状态
            if col == 0:
                return self.RESOURCE_STATE_QBRUSHS[self.theme_kanban.album_kanbans[i].track_res_states[j]]
            # 已有 Mark 信息
            if self.theme_kanban.album_kanbans[i].album.tracks[j].mark:
                return self.MARKED_FOREGROUND_QBRUSHES
 
        # 背景
        if role == Qt.ItemDataRole.BackgroundRole:
            # 已有 Mark 信息
            if self.theme_kanban.album_kanbans[i].album.tracks[j].mark:
                return self.MARKED_BACKGROUND_QBRUSHES

        # 文本对齐
        if role == Qt.ItemDataRole.TextAlignmentRole:
            # Size 列 文本右对齐
            if col in [0]:
                return Qt.AlignmentFlag.AlignRight
            # Date, Mark 列 文本居中
            if col in [4, 5]:
                return Qt.AlignmentFlag.AlignCenter

        # DisplayRole, EditRole
        if role in [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]:
            return self._get_data(role, col, i, j)

        return None

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole) -> Any:

        # 列表头 播放中 仅展示装饰图标
        if orientation == Qt.Orientation.Vertical and self.layout_ps and self.kanban_ij[self.layout_ps[section]] == self.playing_ij:
            if role == Qt.ItemDataRole.DecorationRole:
                return QIcon(f"./assets/playing.png")
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

        if not index.isValid() or row >= len(self.layout_ps) or col >= len(self.headers):
            return False

        # 仅响应 EditRole
        if role != Qt.ItemDataRole.EditRole:
            return False

        # 转字符串
        value = str(value)

        # 更新数据
        i, j = self.kanban_ij[self.layout_ps[row]]
        old_hash = hash(self.theme_kanban.album_kanbans[i].album)

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
        
        if old_hash == hash(self.theme_kanban.album_kanbans[i].album):
            return False

        # 刷新视图
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])
        return True

    def _apply_sort(self) -> None:
        column, order = self.sort_args
        # 忽略大小写，首尾空字符
        self.layout_ps.sort(key=lambda p: self._get_data(Qt.ItemDataRole.EditRole, column, *self.kanban_ij[p]).lower().strip(), 
                            reverse=(order == Qt.SortOrder.DescendingOrder))

    def _apply_filters(self) -> None:
        self.layout_ps = []
        for p, (i, j) in enumerate(self.kanban_ij):
            # 全字包含 或 正则匹配
            if all((t in self._get_data(Qt.ItemDataRole.EditRole, c, i, j) or re.search(t, self._get_data(Qt.ItemDataRole.EditRole, c, i, j))) 
                   for c, t in self.filters.items()):
                self.layout_ps.append(p)
        
        # 应用排序
        self._apply_sort()

    # 内部方法

    def _get_data(self, role: Qt.ItemDataRole, col: int, i: int, j: int) -> str:
        if col == 0:
            stat = self.theme_kanban.album_kanbans[i].track_stat_results[j]
            size = "{:.2f} MiB".format(stat.st_size / 1024 / 1024) if stat else ""
            return size
        elif col == 1:
            return self.theme_kanban.album_kanbans[i].album.tracks[j].title
        elif col == 2:
            return self.theme_kanban.album_kanbans[i].album.tracks[j].artist
        elif col == 3:
            return self.theme_kanban.album_kanbans[i].album.album
        elif col == 4:
            return self.theme_kanban.album_kanbans[i].album.date
        elif col == 5:
            mark = self.theme_kanban.album_kanbans[i].album.tracks[j].mark
            return "🤍" if mark == "1" and role == Qt.ItemDataRole.DisplayRole else mark


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
                        QHeaderView.ResizeMode.Fixed, QHeaderView.ResizeMode.Fixed]
        [header.setSectionResizeMode(i, m) for i, m in enumerate(column_modes)]

        self.setup_context_menu()

    # 重写方法

    def resizeEvent(self, event: QResizeEvent) -> None:
        # 还原默认列宽
        fh = self.fontMetrics().height()
        column_widths = [fh*5, 0, fh*18, fh*18, fh*5, fh*2]
        [w and self.setColumnWidth(i, w) for i, w in enumerate(column_widths)]
        # Title 占据剩余宽度
        self.setColumnWidth(1, self.width() - sum(column_widths) - self.verticalHeader().width() - self.verticalScrollBar().width())
        return super().resizeEvent(event)



