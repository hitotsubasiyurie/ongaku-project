import re
from typing import Any

from PySide6.QtCore import (QModelIndex, Qt, QAbstractTableModel, QObject, QSortFilterProxyModel, QTimer)


class CustomTableItemModel(QAbstractTableModel):

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)

        self.headers: list[str] = []
        self.table: list[list[str]] = []
        self.row_cnt: int = len(self.table)
        self.col_cnt: int = len(self.headers)

    # 只读

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
        return Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def setData(self, index: QModelIndex, value: Any, role: Qt.ItemDataRole = Qt.ItemDataRole.EditRole) -> bool:
        #  编辑无效
        return True


class CustomTableSortFilterProxyModel(QSortFilterProxyModel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.filters: dict[int, re.Pattern] = {}

        # 防抖定时器
        self._filter_timer = QTimer(self)
        # 仅超时一次
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(500)
        self._filter_timer.timeout.connect(self._apply_filters)

    def set_filter(self, column: int, text: str) -> None:
        if text:
            try:
                self.filters[column] = re.compile(text, re.IGNORECASE)
            except re.error:
                self.filters.pop(column, None)
        else:
            self.filters.pop(column, None)
        
        self._filter_timer.start()

    def unset_filter(self) -> None:
        self.filters = {}
        self._apply_filters()

    # 重写方法

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        if not self.filters:
            return True

        model = self.sourceModel()
        for col, pattern in self.filters.items():
            idx = model.index(source_row, col, source_parent)
            data = str(model.data(idx, Qt.ItemDataRole.DisplayRole)) or ""
            # 有一列无法匹配 就过滤整行
            if not pattern.search(data):
                return False
        return True

    # 表头

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole) -> Any:
        # 列表头 展示索引 从 1 开始
        if orientation == Qt.Orientation.Vertical and role == Qt.ItemDataRole.DisplayRole:
            return section + 1
        
        return self.sourceModel().headerData(section, orientation, role)

    # 内部方法

    def _apply_filters(self) -> None:
        self.setDynamicSortFilter(False)
        self.invalidateFilter()
        self.setDynamicSortFilter(True)

