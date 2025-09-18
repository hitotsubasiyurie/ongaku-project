from PySide6.QtCore import QRect, QModelIndex, Qt, QObject, Signal, QItemSelection, QMimeData
from PySide6.QtGui import QPainter, QDragEnterEvent, QDropEvent, QAction, QPainterPath
from PySide6.QtWidgets import (QFrame, QStyledItemDelegate, QWidget, QStyleOptionViewItem, QTableView, QHeaderView,
    QAbstractItemView, )

from ongaku.kanban.kanban import ResourceState, ThemeKanBan
from ongaku.kanban.theme_colors import current_theme
from ongaku.kanban.custom_table_item_model import CustomTableItemModel


class AlbumTableItemModel(CustomTableItemModel):

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)

        self.headers: list[str] = ["S", "ALBUM", "CATNO", "DATE"]
        self.col_cnt: int = len(self.headers)

    def set_theme_kanban(self, theme_kanban: ThemeKanBan = None) -> None:
        # 声明重置模型
        self.beginResetModel()

        # 重置数据
        self.table = []
        # 默认 以 S 列 排序
        self.sort_args = (0, Qt.SortOrder.DescendingOrder)
        self.filters = {}

        if theme_kanban:
            self.table = [[(k.album_res_state, k.metadata_state), k.album.album, k.album.catalognumber, k.album.date]
                        for k in theme_kanban.album_kanbans]
        
        self.layout_ps = list(range(len(self.table)))
        # 应用排序
        self._apply_sort()
        self.row_cnt = len(self.layout_ps)

        self.endResetModel()

    # 可编辑

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        # S 列 只读
        if index.column() == 0:
            return Qt.ItemFlag.NoItemFlags
        
        # 允许 拖入
        return (Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDropEnabled)
    
    # drop 支持
    
    def supportedDropActions(self) -> Qt.DropAction:
        return Qt.DropAction.CopyAction | Qt.DropAction.MoveAction
    
    def canDropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int, parent: QModelIndex) \
            -> bool:
        return True


class AlbumStateItemDelegate(QStyledItemDelegate):
    """
    根据 ResourceState 绘制不同颜色，根据 MetadataState 绘制不同圆心角的扇形。
    """

    RESOURCE_STATE_COLORS = {
        ResourceState.LOSSLESS: current_theme.LOSSLESS_COLOR,
        ResourceState.LOSSY: current_theme.LOSSY_COLOR,
        ResourceState.MISSING: current_theme.MISSING_COLOR,
    }

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()
        rs, ms = index.data(Qt.ItemDataRole.DisplayRole)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.RESOURCE_STATE_COLORS[rs])
        # 抗锯齿
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
        self.item_model = AlbumTableItemModel(self)
        self.setModel(self.item_model)
        # 重置、排序、筛选 后 滚动至开头
        self.item_model.layoutChanged.connect(self.scrollToTop)

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
        # 条目滚动 提高性能
        self.setVerticalScrollMode(QTableView.ScrollMode.ScrollPerItem)
        # 允许拖入
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setDropIndicatorShown(True)

        # 字体高度
        fh = self.fontMetrics().height()

        # 设置行
        header = self.verticalHeader()
        header.setDefaultSectionSize(fh)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header.setSectionsClickable(False)
        header.setFrameShape(QFrame.Shape.NoFrame)
        
        # 设置列
        header = self.horizontalHeader()
        column_widths = [fh*1.5, 0, fh*6, fh*5]
        [self.setColumnWidth(i, w) for i, w in enumerate(column_widths)]
        column_modes = [QHeaderView.ResizeMode.Fixed if w else QHeaderView.ResizeMode.Stretch for w in column_widths]
        [header.setSectionResizeMode(i, m) for i, m in enumerate(column_modes)]

        self.setup_context_menu()

    # 重写方法

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        # 拖入内容时 激活窗口
        self.activateWindow()
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        self.paths_dropped.emit(paths)
        event.acceptProposedAction()

