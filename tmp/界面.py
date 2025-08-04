import sys
import os

sys.path.append(r"E:\my\ongaku")
os.environ["ONGAKU_METADATA_PATH"] = r"D:\ongaku-metadata"
os.environ["ONGAKU_RESOURCE_PATH"] = r"D:\移动云盘同步盘\ongaku-resource"
os.environ["ONGAKU_TMP_PATH"] = r"D:\ongaku-tmp"

from PySide6.QtWidgets import QApplication

from ongaku.gui.main_window import MainWindow


if __name__ == "__main__":
    app = QApplication([])
    font = app.font()
    font.setPixelSize(11)
    font.setFamily("Helvetica Neue")
    app.setFont(font)
    widget = MainWindow()
    screen = app.screens()[0]
    screen_geometry = screen.availableGeometry()
    width = screen_geometry.width()
    height = int(screen_geometry.height() * 0.5)
    widget.resize(width, height)
    widget.move(screen_geometry.left(), screen_geometry.top())
    widget.show()
    sys.exit(app.exec())








