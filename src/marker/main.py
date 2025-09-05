import os
import sys
import ctypes
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PySide6.QtWidgets import QApplication

from src.marker.track_table_widget import TrackTableView
from src.kanban.kanban import ThemeKanBan


if __name__ == "__main__":
    # 隐藏 cmd 窗口
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

    app = QApplication([])
    font = app.font()
    font.setPixelSize(11)
    font.setFamily("Helvetica Neue")
    app.setFont(font)
    widget = TrackTableView()
    screen = app.screens()[0]
    screen_geometry = screen.availableGeometry()
    width = screen_geometry.width()
    height = int(screen_geometry.height() * 0.5)
    widget.resize(width, height)
    widget.set_theme_kanban(ThemeKanBan(r"D:\ongaku-metadata\アイドルマスター [偶像大师] [THE IDOLM@STER].toml", r"D:\移动云盘同步盘\ongaku-resource\アイドルマスター [偶像大师] [THE IDOLM@STER]"))
    widget.move(screen_geometry.left(), screen_geometry.top())
    widget.show()
    sys.exit(app.exec())








