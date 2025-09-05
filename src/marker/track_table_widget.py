from typing import Any

from PySide6.QtCore import (QRect, QModelIndex, Qt, QAbstractItemModel, QObject, Signal, QItemSelection, QMimeData, 
    QRectF, )
from PySide6.QtGui import (QColor, QPainter, QDragEnterEvent, QDropEvent, QDragMoveEvent, QAction, QPainterPath, )
from PySide6.QtWidgets import (QFrame, QStyledItemDelegate, QWidget, QStyleOptionViewItem, QTableView, QHeaderView,
                               QAbstractItemView, )

from src.basemodels import Album, Track
from src.kanban.kanban import ThemeKanBan


class TrackTableItemModel(QAbstractItemModel):

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)

        self.headers: list[str] = ["Size", "Title", "Artist", "Album", "Date", "Mark"]
        self.table: list[list[str]] = []
        self.row_cnt: int = 0
        self.col_cnt: int = 6

        # 记忆 模型 排序状态
        self.sort_args: tuple[Any, ...] = None

    def set_theme_kanban(self, theme_kanban: ThemeKanBan) -> None:
        self.table = []
        # 保留原始索引信息
        self._original_index = []
        for i, k in enumerate(theme_kanban.album_kanbans):
            for j in range(len(k.album.tracks)):
                stat = k.track_stat_results[j]
                size = "{:.2f} MB".format(stat.st_size / 1024 / 1024) if stat else ""
                self.table.append([size, k.album.tracks[j].title, k.album.tracks[j].artist, 
                                   k.album.album, k.album.date, k.album.mark])
                self._original_index.append([i, j])

        self.row_cnt = len(self.table)
        self.col_cnt = len(self.headers)

    # 只读

    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        # parent 无效时，指向 root item
        if not parent.isValid() and row < self.row_cnt:
            return self.createIndex(row, column)
        return QModelIndex()

    def parent(self, child: QModelIndex = QModelIndex()) -> QModelIndex:
        return QModelIndex()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if not parent.isValid():
            return self.row_cnt
        return 0

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return self.col_cnt

    def data(self, index: QModelIndex, role: Qt.ItemDataRole = None) -> Any:
        row, col = index.row(), index.column()
        
        if not index.isValid() or row >= self.row_cnt or col >= self.col_cnt:
            return None
        
        # 返回原始索引信息
        if role == Qt.ItemDataRole.UserRole:
            return self._original_index[row]

        if role in [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]:
            return self.table[row][col]

        return None

    # 排序

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        if not self.table:
            return
        # 声明数据仍然有效，只是布局变化
        self.layoutAboutToBeChanged.emit()
        # 原始数据 需要 参与排序
        combined = sorted(zip(self.table, self._original_index), 
                          key=lambda x: x[0][column], 
                          reverse=(order==Qt.SortOrder.DescendingOrder))
        self.table, self._original_index = map(list, zip(*combined))
        self.layoutChanged.emit()
        # 更新排序状态
        self.sort_args = (column, order)

    # 表头

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return

        # 列表头 展示索引 从 1 开始
        if orientation == Qt.Orientation.Vertical:
            return section + 1
        
        return self.headers[section] if section < len(self.headers) else None
    
    # 可编辑

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        return Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def setData(self, index: QModelIndex, value: Any, role: Qt.ItemDataRole = Qt.ItemDataRole.EditRole) -> bool:
        #  编辑无效
        return True


# TODO: size 用绿色黄色字体标明有损无损
# TODO: 部分列居中

class TrackTableView(QTableView):

    def setup_context_menu(self) -> None:
        # 初始化 右键菜单
        pass

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        # 设置模型
        model = TrackTableItemModel()
        self.setModel(model)

        # 表格无边框
        self.setShowGrid(False)
        self.setFrameShape(QFrame.Shape.NoFrame)
        # 可编辑
        self.setEditTriggers(QTableView.EditTrigger.DoubleClicked)
        # 多选
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        # 可排序
        self.setSortingEnabled(True)
        # 像素滚动
        self.setVerticalScrollMode(QTableView.ScrollMode.ScrollPerPixel)
        # 隐藏滚动条
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # 字体大小
        font_size = self.font().pixelSize()

        # 设置行
        header = self.verticalHeader()
        # header.setFixedWidth(font_size*1.5)
        header.setDefaultSectionSize(font_size*1.5)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header.setSectionsClickable(False)
        header.setFrameShape(QFrame.Shape.NoFrame)

        # 设置 列
        header = self.horizontalHeader()
        column_sizes = [font_size*6, 0, font_size*32, font_size*32, font_size*8, font_size*4]
        [self.setColumnWidth(i, w) for i, w in enumerate(column_sizes)]
        column_modes = [QHeaderView.ResizeMode.Fixed if w else QHeaderView.ResizeMode.Stretch for w in column_sizes]
        [header.setSectionResizeMode(i, m) for i, m in enumerate(column_modes)]

    def set_theme_kanban(self, theme_kanban: ThemeKanBan) -> None:
        model: TrackTableItemModel = self.model()
        # 声明所有数据都无效，重新加载
        model.beginResetModel()
        model.set_theme_kanban(theme_kanban)
        model.endResetModel()

        # 还原排序状态
        model.sort(*(model.sort_args or (0, Qt.SortOrder.DescendingOrder)))






















