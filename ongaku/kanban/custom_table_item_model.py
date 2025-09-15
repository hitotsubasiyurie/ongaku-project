import re
from typing import Any

from PySide6.QtCore import QModelIndex, Qt, QAbstractItemModel, QObject, QTimer


class CustomTableItemModel(QAbstractItemModel):

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)

        self.headers: list[str] = []
        self.table: list[list[str]] = []

        # 布局索引
        self.layout_index: list[int] = []
        self.row_cnt: int = len(self.layout_index)
        self.col_cnt: int = len(self.headers)
        # 排序状态
        self.sort_args: tuple[int, Qt.SortOrder] = (0, Qt.SortOrder.AscendingOrder)
        # 过滤
        self.filters: dict[int, re.Pattern] = {}

        # 防抖定时器
        self._filter_timer = QTimer(self)
        # 仅超时一次
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(500)
        self._filter_timer.timeout.connect(self._apply_filters)

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
        if not parent.isValid():
            return self.col_cnt
        return 0

    def data(self, index: QModelIndex, role: Qt.ItemDataRole = None) -> Any:
        row, col = index.row(), index.column()
        
        if not index.isValid() or row >= self.row_cnt or col >= self.col_cnt:
            return None
        
        # 仅响应 DisplayRole, EditRole
        if role in [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]:
            return self.table[self.layout_index[row]][col]
        
        return None

    # 表头

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole) -> Any:
        # 仅响应 DisplayRole
        if role != Qt.ItemDataRole.DisplayRole:
            return

        # 列表头 展示索引 从 1 开始
        if orientation == Qt.Orientation.Vertical:
            return section + 1
        
        return self.headers[section] if section < self.col_cnt else None
    
    # 可编辑

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        # 基本 item flag
        return Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def setData(self, index: QModelIndex, value: Any, role: Qt.ItemDataRole = Qt.ItemDataRole.EditRole) -> bool:
        #  编辑无效
        return True

    # 排序

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        if not self.table:
            return
        
        # 更新排序状态
        self.sort_args = (column, order)

        # 声明数据仍然有效，只是布局变化
        self.layoutAboutToBeChanged.emit()
        self._apply_sort()
        self.layoutChanged.emit()

    # 自定义方法

    def set_filter(self, column: int, text: str) -> None:
        if not self.table:
            return
        
        if text:
            try:
                self.filters[column] = re.compile(text, re.IGNORECASE)
            except re.error:
                self.filters.pop(column, None)
        else:
            self.filters.pop(column, None)
        
        # 启动定时器
        self._filter_timer.start()
    
    def unset_filter(self) -> None:
        if not self.table:
            return
        
        self.filters = {}

        self._filter_timer.start()

    # 内部方法

    def _apply_sort(self) -> None:
        column, order = self.sort_args
        self.layout_index.sort(key=lambda r: self.table[r][column], 
                               reverse=(order == Qt.SortOrder.DescendingOrder))

    def _apply_filters(self) -> None:
        # 声明数据仍然有效，只是布局变化
        self.layoutAboutToBeChanged.emit()

        self.layout_index = []
        for row, _list in enumerate(self.table):
            if all(pat.search(_list[c]) for c, pat in self.filters.items()):
                self.layout_index.append(row)
        # 更新 行数
        self.row_cnt: int = len(self.layout_index)

        # 应用排序
        self._apply_sort()

        self.layoutChanged.emit()



