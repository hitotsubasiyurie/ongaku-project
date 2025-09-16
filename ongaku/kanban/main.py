import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from PySide6.QtWidgets import QApplication


from ongaku.kanban.kanban import KanBan
from ongaku.kanban.kanban_ui import KanBanUI
from ongaku.kanban.theme_colors import current_theme


if __name__ == "__main__":
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





