import sys

from PySide6.QtWidgets import QApplication

from ongaku.gui.main_window import MainWindow


if __name__ == "__main__":
    app = QApplication([])
    font = app.font()
    font.setPixelSize(11)
    font.setFamily("Helvetica Neue")
    app.setFont(font)
    widget = MainWindow()
    widget.showMaximized()
    sys.exit(app.exec())








