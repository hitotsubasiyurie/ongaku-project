import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTableView,
    QLineEdit, QHeaderView
)
from PySide6.QtCore import QSortFilterProxyModel, Qt
from PySide6.QtGui import QStandardItemModel, QStandardItem


class TableFilterDemo(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QTableView + QSortFilterProxyModel Demo")
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        # 输入框
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("输入关键字筛选表格...")
        layout.addWidget(self.filter_edit)

        # 表格
        self.table = QTableView()
        layout.addWidget(self.table)

        # 原始模型
        self.model = QStandardItemModel(5, 3)  # 5 行 3 列
        self.model.setHorizontalHeaderLabels(["Name", "Age", "City"])

        data = [
            ("Alice", "23", "New York"),
            ("Bob", "30", "London"),
            ("Charlie", "28", "Paris"),
            ("David", "35", "Tokyo"),
            ("Eve", "22", "Berlin"),
        ]

        for row, (name, age, city) in enumerate(data):
            self.model.setItem(row, 0, QStandardItem(name))
            self.model.setItem(row, 1, QStandardItem(age))
            self.model.setItem(row, 2, QStandardItem(city))

        # 筛选代理模型
        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)  # 不区分大小写
        self.proxy.setFilterKeyColumn(-1)  # -1 = 全部列都参与筛选

        self.table.setModel(self.proxy)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # 绑定输入框变化
        self.filter_edit.textChanged.connect(self.proxy.setFilterFixedString)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    demo = TableFilterDemo()
    demo.show()
    sys.exit(app.exec())
