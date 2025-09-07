import os
import sys
import ctypes
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor, Qt

from src.kanban.kanban import KanBan
from src.kanban.kanban_ui import KanBanUI


if __name__ == "__main__":
    # 隐藏 cmd 窗口
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

    app = QApplication([])
    dark_palette = QPalette()

    # 背景和窗口
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(40, 40, 40))

    dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(204, 204, 204))
    dark_palette.setColor(QPalette.ColorRole.Text, QColor(204, 204, 204))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(204, 204, 204))

    # 高亮 同 VSCode
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(38, 79, 120))

    app.setPalette(dark_palette)
    QApplication.setStyle("Fusion")
    app.setStyleSheet(Path(__file__).with_name("widgets").joinpath("widgets.qss").read_text("utf-8"))
    font = app.font()
    font.setPointSize(9)
    font.setFamily("JetBrains Mono")
    app.setFont(font)
    widget = KanBanUI()
    widget.set_kanban(KanBan(r"D:\ongaku-metadata", r"D:\移动云盘同步盘\ongaku-resource"))
    screen = app.screens()[0]
    screen_geometry = screen.availableGeometry()
    width = screen_geometry.width()
    height = int(screen_geometry.height() * 0.5)
    widget.resize(width, height)
    widget.move(screen_geometry.left(), screen_geometry.top())
    widget.show()
    sys.exit(app.exec())








