import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTableView, QVBoxLayout, QWidget, QFrame
)
from PySide6.QtCore import Qt, QSortFilterProxyModel, QAbstractTableModel


# ----------------------------
# 简单数据模型
# ----------------------------
class DemoModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self.headers = ["S", "ALBUM", "CATNO", "DATE"]
        self.data_table = [
            ["ok", "Nevermind", "GEF-24425", "1991"],
            ["ok", "OK Computer", "NODATA-123", "1997"],
            ["ok", "Kid A", "NODATA-456", "2000"],
            ["ok", "In Rainbows", "XL-12345", "2007"],
            ["ok", "The Bends", "NODATA-789", "1995"],
        ]

    def rowCount(self, parent=None):
        return len(self.data_table)

    def columnCount(self, parent=None):
        return len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        return self.data_table[index.row()][index.column()]

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return super().headerData(section, orientation, role)


# ----------------------------
# 代理模型：支持多列过滤
# ----------------------------
class MultiFilterProxyModel(QSortFilterProxyModel):
    def __init__(self):
        super().__init__()
        self.filters = {}

    def setFilterForColumn(self, col, text):
        self.filters[col] = text.lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, row, parent):
        model = self.sourceModel()
        for col, pattern in self.filters.items():
            if not pattern:
                continue
            idx = model.index(row, col, parent)
            val = str(model.data(idx, Qt.DisplayRole)).lower()
            if pattern not in val:
                return False
        return True


# ----------------------------
# 自定义 Header 带输入框
# ----------------------------
from PySide6.QtWidgets import QHeaderView, QLineEdit
from PySide6.QtCore import QRect


class FilterHeader(QHeaderView):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setSectionsMovable(True)
        self.setStretchLastSection(True)
        self.editors = {}

    def addFilterEditor(self, col, callback):
        editor = QLineEdit(self.parent())
        editor.setPlaceholderText(f"Filter {self.model().headerData(col, Qt.Horizontal)}")
        editor.textChanged.connect(lambda text, c=col: callback(c, text))
        editor.setFixedHeight(22)
        self.editors[col] = editor
        editor.show()
        self._adjustPositions()

    def _adjustPositions(self):
        """调整每个过滤框的位置"""
        for col, editor in self.editors.items():
            if not self.isSectionHidden(col):
                left = self.sectionPosition(col) - self.offset()  # 注意减去水平滚动条偏移
                width = self.sectionSize(col)
                editor.setGeometry(QRect(
                    left,
                    self.height(),   # 放在表头底下
                    width,
                    editor.height()
                ))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adjustPositions()

    def sectionResized(self, logicalIndex, oldSize, newSize):
        super().sectionResized(logicalIndex, oldSize, newSize)
        self._adjustPositions()

    def sectionMoved(self, logicalIndex, oldVisualIndex, newVisualIndex):
        super().sectionMoved(logicalIndex, oldVisualIndex, newVisualIndex)
        self._adjustPositions()


# ----------------------------
# 主窗口 Demo
# ----------------------------
class DemoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FilterHeader Demo")

        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 模型
        model = DemoModel()
        proxy = MultiFilterProxyModel()
        proxy.setSourceModel(model)

        # 表格
        table = QTableView()
        table.setModel(proxy)
        table.setSortingEnabled(True)
        table.setSelectionBehavior(QTableView.SelectRows)
        table.setFrameShape(QFrame.NoFrame)

        # 自定义 Header
        header = FilterHeader(Qt.Horizontal, table)
        table.setHorizontalHeader(header)

        # 给 ALBUM, CATNO, DATE 加过滤框
        for col, name in enumerate(model.headers):
            if name in ("ALBUM", "CATNO", "DATE"):
                header.addFilterEditor(col, proxy.setFilterForColumn)

        layout.addWidget(table)
        self.setCentralWidget(widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = DemoWindow()
    w.resize(600, 300)
    w.show()
    sys.exit(app.exec())
