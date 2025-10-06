# example_a.py
from PySide6.QtWidgets import QApplication, QPushButton, QWidget, QVBoxLayout
from PySide6.QtGui import QIcon
import sys

app = QApplication(sys.argv)

w = QWidget()
layout = QVBoxLayout(w)

btn = QPushButton("SVG Icon")
btn.setIcon(QIcon(r"E:\my\ongaku-project\ongaku\ui\assets\dark\page_next.svg"))   # 直接使用 svg 文件
btn.setIconSize(btn.sizeHint())           # 或者设置成合适的 QSize(x,y)
layout.addWidget(btn)

w.show()
sys.exit(app.exec())
