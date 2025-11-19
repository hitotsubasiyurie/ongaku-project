import re
import os
import operator
from typing import Any
from pathlib import Path


from PySide6.QtCore import QRect, QModelIndex, Qt, QObject, Signal, QMimeData, QAbstractItemModel, QTimer
from PySide6.QtGui import QPainter, QDragEnterEvent, QDropEvent, QAction, QPainterPath, QBrush
from PySide6.QtWidgets import (QFrame, QStyledItemDelegate, QWidget, QStyleOptionViewItem, QTableView, QHeaderView,
    QAbstractItemView, QStyle)

from ongaku.core.kanban import KanBan, ThemeKanBan
from ongaku.ui.custom import CustomTableItemModel


class ThemeTableItemModel(CustomTableItemModel):

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)

        self.headers: list[str] = ["Path", "Name", "Start Date", "End Date", "Collect", "Mark"]

        self.kanban: KanBan = None

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

        # DisplayRole, EditRole
        if role in [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]:
            return self._get_data(col, p)

        return None

    def set_filter(self, column: int, text: str) -> None:
        if not self.kanban:
            return
        super().set_filter(column, text)

    # 内部方法

    def _apply_sort(self) -> None:
        column, order = self.sort_args
        # path 列排序
        self.layout_ps.sort(key=lambda p: (self._get_sort_data(0, p), self._get_sort_data(column, p)), 
                            reverse=(order == Qt.SortOrder.DescendingOrder))

    def _apply_filters(self) -> None:
        self.layout_ps = []
        for p in range(len(self.kanban.theme_kanbans)):
            # 全字包含 或 正则匹配
            is_match = all((t in self._get_data(c, p) or re.search(t, self._get_data(c, p))) for c, t in self.filters.items())
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
    pass


class ThemeTableView(QTableView):

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        # 设置模型
        self.item_model = ThemeTableItemModel(self)
        self.setModel(self.item_model)
        # 重置、排序、筛选 后 滚动至开头
        self.item_model.layoutChanged.connect(self.scrollToTop)

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
        column_widths = [0, 0, fh*6, fh*6, fh*6, fh*6]
        [self.setColumnWidth(i, w) for i, w in enumerate(column_widths)]
        column_modes = [QHeaderView.ResizeMode.Fixed if w else QHeaderView.ResizeMode.Stretch for w in column_widths]
        [header.setSectionResizeMode(i, m) for i, m in enumerate(column_modes)]







