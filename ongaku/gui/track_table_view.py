import json
from typing import Any

from PySide6.QtCore import (QRect, QModelIndex, Qt, QAbstractItemModel, QObject, Signal, QMimeData,
                            QSize, )
from PySide6.QtGui import (QColor, QPainter, QDragEnterEvent, QDropEvent, QDragMoveEvent, QFont,
                           QFontMetrics, )
from PySide6.QtWidgets import (QFrame, QStyledItemDelegate, QWidget, QStyleOptionViewItem, QTableView, QHeaderView,
                               QAbstractItemView, )

from ongaku.common.mdf_util import ResourceState
from ongaku.common.metadata import Track
from ongaku.gui.album_table_view import ResourceStateItemDelegate


class TrackTableItemModel(QAbstractItemModel):

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)

        self.set_tracks([], [])

    def set_tracks(self, tracks: list[Track], track_states: list[ResourceState]) -> None:
        self.tracks: list[Track] = tracks
        self.track_states: list[ResourceState] = track_states

        self.headers = ["S", "TITLE"]
        self.table = [[s, (t.title, t.artist)] 
                       for t, s in zip(self.tracks, self.track_states)]

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
        
        if role in [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]:
            return self.table[row][col]
        
        return None

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
        # 资源状态列 只读
        if index.column() == 0:
            return Qt.ItemFlag.NoItemFlags
        
        return (Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDropEnabled)

    def setData(self, index: QModelIndex, value: Any, role: Qt.ItemDataRole = Qt.ItemDataRole.EditRole) -> bool:
        #  编辑无效
        return True

    # drop
    
    def supportedDropActions(self) -> Qt.DropAction:
        return Qt.DropAction.CopyAction | Qt.DropAction.MoveAction
    
    def canDropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int, parent: QModelIndex) \
            -> bool:
        return True


class TrackItemDelegate(QStyledItemDelegate):

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()
        title, artist = index.data(Qt.ItemDataRole.DisplayRole)
        # 艺术家信息 增加缩进
        artist = " "*6 + artist
        rect: QRect = option.rect
        width: int = rect.width()
        font: QFont = option.font
        # 0.5 字符 行距
        title_rect = QRect(rect.left(), rect.top()+font.pixelSize()//2, rect.width(),
                           self._get_content_height(font, width, title))
        painter.drawText(title_rect, title)
        
        artist_rect = QRect(rect.left(), title_rect.bottom(), rect.width(),
                            self._get_content_height(font, width, artist))
        painter.setPen(QColor(0x666666))
        painter.drawText(artist_rect, artist)
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        title, artist = index.data(Qt.ItemDataRole.DisplayRole)
        artist = " "*6 + artist
        font: QFont = option.font
        width: int = option.rect.width()
        # 0.5 字符 行距
        height = (self._get_content_height(font, width, title) + self._get_content_height(font, width, artist)
                  + font.pixelSize())
        return QSize(width, height)

    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        # 被编辑时，展示 json 格式化内容
        editor.setText(json.dumps(index.data(Qt.ItemDataRole.DisplayRole), ensure_ascii=False))

    # 内部方法

    @staticmethod
    def _get_content_height(font: QFont, width: int, text: str) -> int:
        metrics = QFontMetrics(font)
        height = metrics.boundingRect(QRect(0, 0, width, 0), Qt.TextFlag.TextWordWrap, text).height()
        return height


class TrackTableView(QTableView):

    paths_dropped = Signal(list)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        # 初始化模型
        model = TrackTableItemModel()
        self.setModel(model)
        self.setItemDelegateForColumn(0, ResourceStateItemDelegate(self))
        self.setItemDelegateForColumn(1, TrackItemDelegate())

        # 表格无边框
        self.setShowGrid(False)
        self.setFrameShape(QFrame.Shape.NoFrame)
        # 可编辑
        self.setEditTriggers(QTableView.EditTrigger.DoubleClicked)
        # self.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        # 像素滚动
        self.setVerticalScrollMode(QTableView.ScrollMode.ScrollPerPixel)
        # 允许拖入
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setDropIndicatorShown(True)

        # 字体大小
        font_size = self.font().pixelSize()

        # 设置行
        header = self.verticalHeader()
        header.setSectionsClickable(False)
        header.setFrameShape(QFrame.Shape.NoFrame)
        
        # 设置列
        header = self.horizontalHeader()
        column_size = [font_size, 0]
        [self.setColumnWidth(i, w) for i, w in enumerate(column_size)]
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionsClickable(False)

    def set_tracks(self, tracks: list[Track], track_states: list[ResourceState]) -> None:
        model: TrackTableItemModel = self.model()
        # 所有数据都无效，重新加载
        model.beginResetModel()
        model.set_tracks(tracks, track_states)
        model.endResetModel()
        self.resizeRowsToContents()

    # 重写方法

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        # 激活窗口
        self.activateWindow()
        event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        # 拖入时选择整行
        index = self.indexAt(event.position().toPoint())
        if index.isValid():
            self.selectRow(index.row())
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        self.paths_dropped.emit(paths)
        event.acceptProposedAction()


