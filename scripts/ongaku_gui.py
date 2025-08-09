import os
import sys
import ctypes
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication

from src.common.constants import METADATA_PATH, RESOURCE_PATH
from src.gui.main_window import MainWindow


if __name__ == "__main__":
    metadata_dir = input(f"Please input metadata directory ({METADATA_PATH}): ").strip("'\"") or METADATA_PATH
    resource_dir = input(f"Please input resource directory ({RESOURCE_PATH}): ").strip("'\"") or RESOURCE_PATH

    if not metadata_dir or not resource_dir:
        sys.exit(0)

    # 隐藏 cmd 窗口
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

    app = QApplication([])
    font = app.font()
    font.setPixelSize(11)
    font.setFamily("Helvetica Neue")
    app.setFont(font)
    widget = MainWindow(metadata_dir, resource_dir)
    screen = app.screens()[0]
    screen_geometry = screen.availableGeometry()
    width = screen_geometry.width()
    height = int(screen_geometry.height() * 0.5)
    widget.resize(width, height)
    widget.move(screen_geometry.left(), screen_geometry.top())
    widget.show()
    sys.exit(app.exec())








