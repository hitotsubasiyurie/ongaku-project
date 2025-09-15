import os
import sys
import ctypes
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PySide6.QtWidgets import QApplication


from ongaku.kanban.kanban import KanBan
from ongaku.kanban.kanban_ui import KanBanUI
from ongaku.kanban.theme_colors import current_theme
from ongaku.kanban.page2.page2_widget import Page2Widget


if __name__ == "__main__":
    # 隐藏 cmd 窗口
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

    app = QApplication([])
    QApplication.setStyle("Fusion")
    current_theme.apply_theme(app)
    app.setStyleSheet(Path(__file__).with_name("widgets.qss").read_text("utf-8"))
    font = app.font()
    font.setPointSize(9)
    font.setFamily("JetBrains Mono")
    app.setFont(font)
    widget = KanBanUI()
    kanban = KanBan(r"D:\ongaku-metadata", r"D:\移动云盘同步盘\ongaku-resource")
    widget.set_kanban(kanban)
    screen = app.screens()[0]
    screen_geometry = screen.availableGeometry()
    width = screen_geometry.width()
    height = int(screen_geometry.height() * 0.5)
    widget.resize(width, height)
    widget.move(screen_geometry.left(), screen_geometry.top())
    widget.show()
    sys.exit(app.exec())





