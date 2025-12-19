import operator
import re
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import QRect, QModelIndex, Qt, QObject, Signal
from PySide6.QtGui import QPainter, QAction, QPalette, QIcon
from PySide6.QtWidgets import (QFrame, QStyledItemDelegate, QWidget, QStyleOptionViewItem, QTableView, QHeaderView,
                               QAbstractItemView)

from src.core.kanban import KanBan
from src.core.settings import global_settings
from src.ui.color_theme import current_theme
from src.ui.custom import CustomTableItemModel


class ThemeTableItemModel(CustomTableItemModel):

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)

        self.headers: list[str] = ["Path", "Name", "Start Date", "End Date", "Collect", "Mark"]

        self.kanban: Optional[KanBan] = None
        # 当前选择的主题看板 指针
        self.current_theme_kanban_p: int = None

    def reset_kanban(self, kanban: KanBan = None) -> None:
        # 声明重置模型
        self.beginResetModel()

        # 重置数据
        self.kanban = kanban

        # 默认 以 End Date 列 排序
        self.sort_args = (3, Qt.SortOrder.DescendingOrder)
        # 默认 无筛选
        self.filters = {}

        # 生成 layout_ps 、筛选、排序 
        self._apply_filters()

        self.endResetModel()

    def data(self, index: QModelIndex, role: Qt.ItemDataRole = None) -> Any:
        row, col = index.row(), index.column()

        if not index.isValid() or row >= len(self.layout_ps) or col >= len(self.headers):
            return None

        p = self.layout_ps[row]

        # 自定义 进度条 数据
        if role == Qt.ItemDataRole.UserRole:
            if col == 1:
                return self._get_sort_data(4, p), self._get_sort_data(5, p)
        
        # 文本对齐
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col == 0:
                return Qt.AlignmentFlag.AlignLeft
            if col in (2, 3, 4, 5):
                return Qt.AlignmentFlag.AlignCenter
        
        # DisplayRole, EditRole
        if role in [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]:
            return self._get_data(col, p)

        return None

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole) -> Any:

        # 列表头 播放中 仅展示装饰图标
        if orientation == Qt.Orientation.Vertical and self.layout_ps and self.layout_ps[section] == self.current_theme_kanban_p:
            if role == Qt.ItemDataRole.DecorationRole:
                return QIcon(f"./assets/{global_settings.ui_color_theme}/locate.png")
            else:
                return
        
        return super().headerData(section, orientation, role)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        # Path 列 不可编辑
        if index.column() == 0:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        
        return super().flags(index)

    def set_filter(self, column: int, text: str) -> None:
        if not self.kanban:
            return
        super().set_filter(column, text)

    ######## 内部方法 ########

    def _apply_sort(self) -> None:
        if not self.layout_ps:
            return
        
        column, order = self.sort_args
        # path 列排序
        self.layout_ps.sort(key=lambda p: (self._get_sort_data(0, p), self._get_sort_data(column, p)), 
                            reverse=(order == Qt.SortOrder.DescendingOrder))

    def _apply_filters(self) -> None:
        self.layout_ps = []
        for p in range(len(self.kanban.theme_kanbans)):
            # 全字包含 或 正则匹配
            is_match = all((t.lower() in self._get_data(c, p).lower() 
                            or re.search(t, self._get_data(c, p), re.IGNORECASE)) for c, t in self.filters.items())
            if not self.filters or is_match:
                self.layout_ps.append(p)
        
        # 应用排序
        self._apply_sort()

    def _get_data(self, col: int, p: int) -> str:
        if col == 0:
            return str(Path(self.kanban.theme_kanbans[p].theme_metadata_file).relative_to(self.kanban.metadata_dir).parent)
        elif col == 1:
            return self.kanban.theme_kanbans[p].theme_name
        elif col == 2:
            return self.kanban.theme_kanbans[p].start_date
        elif col == 3:
            return self.kanban.theme_kanbans[p].end_date
        elif col == 4:
            return "/".join(map(str, self.kanban.theme_kanbans[p].album_collection_progress))
        elif col == 5:
            return "/".join(map(str, self.kanban.theme_kanbans[p].track_mark_progress))

    def _get_sort_data(self, col: int, p: int) -> str:
        if col == 4:
            return operator.truediv(*self.kanban.theme_kanbans[p].album_collection_progress)
        elif col == 5:
            return operator.truediv(*self.kanban.theme_kanbans[p].track_mark_progress)
        # 字符串 不区分 大小写
        return self._get_data(col, p).lower().strip()


class ThemeTableItemDelegate(QStyledItemDelegate):

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        rect: QRect = option.rect
        
        # 选中时不绘制高亮
        # 覆盖绘制 基背景
        painter.fillRect(rect, option.palette.color(QPalette.ColorRole.Base))

        # 先画长进度条
        coll_p, mark_p = index.data(Qt.ItemDataRole.UserRole)
        if coll_p == mark_p != 0:
            coll_p -= 0.01
        params = [(coll_p, current_theme.THEME_PROGRESS_COLL_COLOR),
                  (mark_p, current_theme.THEME_PROGRESS_MARK_COLOR)]
        params.sort(key=lambda t: t[0], reverse=True)
        
        for val, color in params:
            w = int(rect.width() * val)
            progress_rect = QRect(rect.left(), rect.top(), w, rect.height())
            painter.fillRect(progress_rect, color)

        # 绘制文字
        text = index.data()
        painter.drawText(option.rect, Qt.AlignmentFlag.AlignLeft, text)


class ThemeTableView(QTableView):

    action_edit_clicked = Signal()

    def setup_context_menu(self) -> None:
        # 初始化 右键菜单
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        action = QAction("Open Metadata File", self)
        action.triggered.connect(self.action_edit_clicked.emit)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        # 设置模型
        self.item_model = ThemeTableItemModel(self)
        self.setModel(self.item_model)
        # 重置、排序、筛选 后 滚动至开头
        self.item_model.layoutChanged.connect(self.scrollToTop)

        self.setItemDelegateForColumn(1, ThemeTableItemDelegate(self))

        # 表格无边框
        self.setShowGrid(False)
        self.setFrameShape(QFrame.Shape.NoFrame)
        # 可编辑
        self.setEditTriggers(QTableView.EditTrigger.DoubleClicked)
        # 行选择
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        # 单选
        self.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        # 可排序
        self.setSortingEnabled(True)
        # 条目滚动 提高性能
        self.setVerticalScrollMode(QTableView.ScrollMode.ScrollPerItem)
        # 隐藏水平滚动条
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
        # 最小列宽
        header.setMinimumSectionSize(fh*2)
        # ResizeMode
        column_modes = [QHeaderView.ResizeMode.ResizeToContents, 
                        QHeaderView.ResizeMode.Stretch, QHeaderView.ResizeMode.ResizeToContents, QHeaderView.ResizeMode.ResizeToContents, 
                        QHeaderView.ResizeMode.ResizeToContents, QHeaderView.ResizeMode.ResizeToContents]
        [header.setSectionResizeMode(i, m) for i, m in enumerate(column_modes)]

        self.setup_context_menu()

