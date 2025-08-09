import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication

from src.common.constants import METADATA_PATH, RESOURCE_PATH
from src.gui.main_window import MainWindow


if __name__ == "__main__":
    METADATA_PATH = r"D:\ongaku-metadata"
    RESOURCE_PATH = r"D:\移动云盘同步盘\ongaku-resource"
    metadata_dir = input(f"Please input metadata directory ({METADATA_PATH}): ").strip("'\"") or METADATA_PATH
    resource_dir = input(f"Please input resource directory ({RESOURCE_PATH}): ").strip("'\"") or RESOURCE_PATH

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








