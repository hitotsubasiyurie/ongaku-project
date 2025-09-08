import os
import sys
import ctypes
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PySide6.QtWidgets import QApplication


from src.kanban.kanban import KanBan
from src.kanban.kanban_ui import KanBanUI
from src.kanban.theme_colors import current_theme


if __name__ == "__main__":
    # 隐藏 cmd 窗口
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

    app = QApplication([])
    current_theme.apply_theme(app)

    QApplication.setStyle("Fusion")
    app.setStyleSheet(Path(__file__).with_name("widgets.qss").read_text("utf-8"))
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








