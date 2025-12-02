from typing import Any

from PySide6.QtCore import QModelIndex, Qt, QAbstractItemModel, QObject, QTimer


class CustomTableItemModel(QAbstractItemModel):

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)

        self.headers: list[str] = []
        # 布局 真实行指针
        self.layout_ps: list[int] = []
        
        # 排序状态
        self.sort_args: tuple[int, Qt.SortOrder] = (0, Qt.SortOrder.AscendingOrder)
        # 过滤
        self.filters: dict[int, str] = {}

        # 过滤 防抖定时器
        self._filter_timer = QTimer(self)
        # 仅超时一次
        self._filter_timer.setSingleShot(True)
        # 0.5 秒
        self._filter_timer.setInterval(500)

        self._filter_timer.timeout.connect(lambda: [self.layoutAboutToBeChanged.emit(), 
                                                    self._apply_filters(), 
                                                    self.layoutChanged.emit()])

    # 只读

    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        # parent 无效时，指向 root item
        if not parent.isValid() and row < len(self.layout_ps):
            return self.createIndex(row, column)
        return QModelIndex()

    def parent(self, child: QModelIndex = QModelIndex()) -> QModelIndex:
        return QModelIndex()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if not parent.isValid():
            return len(self.layout_ps)
        return 0

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.headers)

    def data(self, index: QModelIndex, role: Qt.ItemDataRole = None) -> Any:
        """
        待实现
        """
        pass

    # 表头

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole) -> Any:
        # 仅响应 DisplayRole
        if role != Qt.ItemDataRole.DisplayRole:
            return

        # 列表头 展示索引 从 1 开始
        if orientation == Qt.Orientation.Vertical:
            return section + 1
        
        return self.headers[section] if section < len(self.headers) else None

    # 可编辑

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.ItemIsEnabled
        
        # 基本 item flag
        return Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def setData(self, index: QModelIndex, value: Any, role: Qt.ItemDataRole = Qt.ItemDataRole.EditRole) -> bool:
        """
        待实现
        """
        pass

    # 排序

    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        # 更新排序状态
        self.sort_args = (column, order)

        # 声明数据仍然有效，只是布局变化
        self.layoutAboutToBeChanged.emit()
        self._apply_sort()
        self.layoutChanged.emit()

    # 自定义方法

    def set_filter(self, column: int, text: str) -> None:
        if text:
            self.filters[column] = text
        else:
            self.filters.pop(column, None)
        
        # 启动定时器
        self._filter_timer.start()

    #################### 内部方法 ####################

    def _apply_sort(self) -> None:
        """
        待实现
        """
        pass

    def _apply_filters(self) -> None:
        """
        待实现
        """
        pass

