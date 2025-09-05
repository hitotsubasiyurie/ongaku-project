from typing import Any

from PySide6.QtCore import (QRect, QModelIndex, Qt, QAbstractItemModel, QObject, Signal, QItemSelection, QMimeData, 
    QRectF, )
from PySide6.QtGui import (QColor, QPainter, QDragEnterEvent, QDropEvent, QDragMoveEvent, QAction, QPainterPath, )
from PySide6.QtWidgets import (QFrame, QStyledItemDelegate, QWidget, QStyleOptionViewItem, QTableView, QHeaderView,
                               QAbstractItemView, )

from src.kanban.kanban import MetadataState, ResourceState
from src.basemodels import Album


class AlbumTableItemModel(QAbstractItemModel):

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)

        self.set_albums([], [], [])

        # 模型 排序状态
        self.sort_args = None

    def set_albums(self, albums: list[Album], metadata_states: list[MetadataState], 
                   resource_states: list[ResourceState]) -> None:
        self.albums: list[Album] = albums
        self.metadata_states: list[MetadataState] = metadata_states
        self.resource_states: list[ResourceState] = resource_states

        self.headers = ["S", "ALBUM", "CATNO", "DATE"]
        # (资源状态, 元数据状态) 排序优先级
        self.table = [[(rs, ms), a.album, a.catalognumber, a.date] 
                       for a, ms, rs in zip(self.albums, self.metadata_states, self.resource_states)]

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

    # 排序

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        if not self.albums:
            return
        # 数据仍然有效，只是布局变化
        self.layoutAboutToBeChanged.emit()
        # 原始数据 一起 排序
        combined = sorted(zip(self.table, self.albums, self.metadata_states, self.resource_states), 
                          key=lambda x: x[0][column], 
                          reverse=(order==Qt.SortOrder.DescendingOrder))
        self.table, self.albums, self.metadata_states, self.resource_states = map(list, zip(*combined))
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
        # 资源状态列 只读
        if index.column() == 0:
            return Qt.ItemFlag.NoItemFlags
        
        return (Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDropEnabled)

    def setData(self, index: QModelIndex, value: Any, role: Qt.ItemDataRole = Qt.ItemDataRole.EditRole) -> bool:
        #  编辑无效
        return True

    # drop 支持
    
    def supportedDropActions(self) -> Qt.DropAction:
        return Qt.DropAction.CopyAction | Qt.DropAction.MoveAction
    
    def canDropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int, parent: QModelIndex) \
            -> bool:
        return True


class AlbumStateItemDelegate(QStyledItemDelegate):

    RESOURCE_STATE_COLORS = {
        ResourceState.LOSSLESS: QColor(0x99CC66),
        ResourceState.LOSSY: QColor(0xFFCC00),
        ResourceState.MISSING: QColor(0xDDDDDD),
    }

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()
        rs, ms = index.data(Qt.ItemDataRole.DisplayRole)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.RESOURCE_STATE_COLORS[rs])
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        rect: QRect = option.rect
        center = rect.center()
        radius = min(rect.width(), rect.height()) / 2 - 1
        diameter = radius * 2
        left, top = center.x() - radius, center.y() - radius

        path = QPainterPath()
        path.moveTo(center)

        # 六种元数据状态 平分 360 度
        # 正下方开始 顺时针旋转
        path.arcTo(left, top, diameter, diameter, 270, -(bin(ms).count("1")*60))
        path.lineTo(center)

        path.closeSubpath()

        painter.drawPath(path)
        painter.restore()

class AlbumTableView(QTableView):

    selected_changed = Signal()
    paths_dropped = Signal(list)
    action_edit_clicked = Signal()
    action_locate_clicked = Signal()

    def setup_context_menu(self) -> None:
        # 初始化 右键菜单
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        action = QAction("Open Metadata File", self)
        action.triggered.connect(self.action_edit_clicked.emit)
        self.addAction(action)
        action = QAction("Locate Resource", self)
        action.triggered.connect(self.action_locate_clicked.emit)
        self.addAction(action)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        # 设置模型
        model = AlbumTableItemModel()
        self.setModel(model)
        self.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self.setItemDelegateForColumn(0, AlbumStateItemDelegate(self))

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
        # 允许拖入
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setDropIndicatorShown(True)

        # 字体大小
        font_size = self.font().pixelSize()

        # 设置行
        header = self.verticalHeader()
        header.setDefaultSectionSize(font_size)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header.setSectionsClickable(False)
        header.setFrameShape(QFrame.Shape.NoFrame)
        
        # 设置列
        header = self.horizontalHeader()
        column_size = [font_size, 0, font_size*8, font_size*6]
        [self.setColumnWidth(i, w) for i, w in enumerate(column_size)]
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)

        self.setup_context_menu()

    def set_albums(self, albums: list[Album], metadata_states: list[MetadataState], 
                   resource_states: list[ResourceState]) -> None:
        model: AlbumTableItemModel = self.model()
        # 所有数据都无效，重新加载
        model.beginResetModel()
        model.set_albums(albums, metadata_states, resource_states)
        model.endResetModel()

        # 还原排序状态
        model.sort(*(model.sort_args or (0, Qt.SortOrder.DescendingOrder)))

    # 重写方法

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        # 激活窗口
        self.activateWindow()
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        self.paths_dropped.emit(paths)
        event.acceptProposedAction()

    # 内部方法

    def _on_selection_changed(self, selected: QItemSelection, deselected: QItemSelection) -> None:
        if not self.selectedIndexes():
            return
        # 有选中才发出信号
        self.selected_changed.emit()

