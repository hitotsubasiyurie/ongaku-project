import re
from typing import Any

from PySide6.QtCore import QRect, QModelIndex, Qt, QObject, Signal, QMimeData
from PySide6.QtGui import QPainter, QDragEnterEvent, QDropEvent, QAction, QPainterPath, QBrush
from PySide6.QtWidgets import (QFrame, QStyledItemDelegate, QWidget, QStyleOptionViewItem, QTableView, QHeaderView,
    QAbstractItemView, QStyle)

from ongaku.core.logger import logger
from ongaku.core.kanban import ResourceState, ThemeKanBan
from ongaku.kanban_ui.color_theme import current_theme
from ongaku.kanban_ui.custom.custom_table_item_model import CustomTableItemModel


class AlbumTableItemModel(CustomTableItemModel):

    MARKED_BACKGROUND_QBRUSHES = QBrush(current_theme.MARKED_BACKGROUND_COLOR)
    MARKED_FOREGROUND_QBRUSHES = QBrush(current_theme.MARKED_FOREGROUND_COLOR)

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)

        self.headers = ["S", "ALBUM", "CATNO", "DATE"]

        self.theme_kanban: ThemeKanBan = None

    def reset_theme_kanban(self, theme_kanban: ThemeKanBan = None) -> None:
        # 声明重置模型
        self.beginResetModel()

        # 重置数据
        self.theme_kanban = theme_kanban
        self.layout_ps = list(range(len(self.theme_kanban.album_kanbans))) if theme_kanban else []

        # 默认 以 S 列 排序
        self.sort_args = (0, Qt.SortOrder.DescendingOrder)
        # 清空筛选
        self.filters = {}

        # 应用排序
        self._apply_sort()

        self.endResetModel()

    def data(self, index: QModelIndex, role: Qt.ItemDataRole = None) -> Any:
        row, col = index.row(), index.column()

        if not index.isValid() or row >= len(self.layout_ps) or col >= len(self.headers):
            return None
        
        p = self.layout_ps[row]

        # 前景
        if role == Qt.ItemDataRole.ForegroundRole:
            # 所有 track 都有 Mark 信息
            if all(t.mark for t in self.theme_kanban.album_kanbans[p].album.tracks):
                return self.MARKED_FOREGROUND_QBRUSHES
 
        # 背景
        if role == Qt.ItemDataRole.BackgroundRole:
            # 所有 track 都有 Mark 信息
            if all(t.mark for t in self.theme_kanban.album_kanbans[p].album.tracks):
                return self.MARKED_BACKGROUND_QBRUSHES

        # DisplayRole, EditRole
        if role in [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]:
            return self._get_data(col, p)

        return None

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole) -> Any:

        if role == Qt.ItemDataRole.TextAlignmentRole and orientation == Qt.Orientation.Vertical:
            return Qt.AlignmentFlag.AlignLeft

        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Vertical:
            if self.theme_kanban.album_kanbans[self.layout_ps[section]].is_favourite:
                return f"🤍"

        return super().headerData(section, orientation, role)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        # S 列 只读
        if index.column() == 0:
            return Qt.ItemFlag.NoItemFlags
        
        # 允许 拖入
        return (Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDropEnabled)

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
        p = self.layout_ps[row]
        old_hash = hash(self.theme_kanban.album_kanbans[p].album)

        if col == 1:
            self.theme_kanban.album_kanbans[p].album.album = value
        if col == 2:
            self.theme_kanban.album_kanbans[p].album.catalognumber = value
        if col == 3:
            self.theme_kanban.album_kanbans[p].album.date = value


        if old_hash == hash(self.theme_kanban.album_kanbans[p].album):
            return False

        # 刷新视图
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])
        return True

    # drop 支持
    
    def supportedDropActions(self) -> Qt.DropAction:
        return Qt.DropAction.CopyAction | Qt.DropAction.MoveAction
    
    def canDropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int, parent: QModelIndex) \
            -> bool:
        return True

    def set_filter(self, column: int, text: str) -> None:
        if not self.theme_kanban:
            return
        super().set_filter(column, text)

    def _apply_sort(self) -> None:
        column, order = self.sort_args
        
        # 忽略大小写，首尾空字符
        self.layout_ps.sort(key=lambda p: self._get_data(column, p) if column == 0 else self._get_data(column, p).lower().strip(), 
                            reverse=(order == Qt.SortOrder.DescendingOrder))

    def _apply_filters(self) -> None:
        self.layout_ps = []
        for p in range(len(self.theme_kanban.album_kanbans)):
            # 全字包含 或 正则匹配
            if all((t in self._get_data(c, p) or re.search(t, self._get_data(c, p))) 
                   for c, t in self.filters.items()):
                self.layout_ps.append(p)
        
        # 应用排序
        self._apply_sort()

    # 内部方法

    def _get_data(self, col: int, p: int) -> str:
        if col == 0:
            return (self.theme_kanban.album_kanbans[p].album_res_state, 
                    self.theme_kanban.album_kanbans[p].metadata_state)
        elif col == 1:
            return self.theme_kanban.album_kanbans[p].album.album
        elif col == 2:
            return self.theme_kanban.album_kanbans[p].album.catalognumber
        elif col == 3:
            return self.theme_kanban.album_kanbans[p].album.date


class AlbumStateItemDelegate(QStyledItemDelegate):
    """
    根据 ResourceState 绘制不同颜色，根据 MetadataState 绘制不同圆心角的扇形。
    """

    RESOURCE_STATE_COLORS = {
        ResourceState.LOSSLESS: current_theme.LOSSLESS_COLOR,
        ResourceState.LOSSY: current_theme.LOSSY_COLOR,
        ResourceState.PARTIAL: current_theme.PARTIAL_COLOR,
        ResourceState.MISSING: current_theme.MISSING_COLOR,
    }

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        # 绘制背景
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        elif (bg := index.data(Qt.ItemDataRole.BackgroundRole)):
            painter.fillRect(option.rect, QBrush(bg))
        
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
    action_delete_clicked = Signal()
    action_locate_clicked = Signal()
    action_search_cover_clicked = Signal()

    def setup_context_menu(self) -> None:
        # 初始化 右键菜单
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        action = QAction("Open Metadata File", self)
        action.triggered.connect(self.action_edit_clicked.emit)
        self.addAction(action)
        action = QAction("Delete Albums", self)
        action.triggered.connect(self.action_delete_clicked.emit)
        self.addAction(action)
        action = QAction("Locate Resource", self)
        action.triggered.connect(self.action_locate_clicked.emit)
        self.addAction(action)
        action = QAction("Search Cover", self)
        action.triggered.connect(self.action_search_cover_clicked.emit)
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
        # 隐藏滚动条
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
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
        column_widths = [fh*1.5, 0, fh*7, fh*6]
        [self.setColumnWidth(i, w) for i, w in enumerate(column_widths)]
        column_modes = [QHeaderView.ResizeMode.Fixed if w else QHeaderView.ResizeMode.Stretch for w in column_widths]
        [header.setSectionResizeMode(i, m) for i, m in enumerate(column_modes)]

        self.setup_context_menu()

    def get_selected_ps(self) -> list[int]:
        # selectedIndexes 以索引为单位，一行多个
        rows = list(sorted(set(i.row() for i in self.selectedIndexes())))
        # 原始数据行指针
        ps = [self.item_model.layout_ps[r] for r in rows]
        return ps

    # 重写方法

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        # 拖入内容时 激活窗口
        self.activateWindow()
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        self.paths_dropped.emit(paths)
        event.acceptProposedAction()

