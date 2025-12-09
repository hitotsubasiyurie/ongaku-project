import os
import sys
from pathlib import Path

executable = Path(sys.argv[0])

# 若是源码运行 添加导包路径
if executable.suffix == ".py":
    sys.path[0] = str(executable.parent.parent.parent)
    os.chdir(executable.parent.parent.parent)
else:
    os.chdir(executable.parent)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

from src.core.settings import global_settings
from src.core.kanban import KanBan
from src.ui.toast_notifier import ToastNotifier
from src.ui.main_window import MainWindow
from src.ui.color_theme import current_theme


if __name__ == "__main__":
    app = QApplication([])
    app.setWindowIcon(QIcon("./assets/icon.png"))

    QApplication.setStyle("Fusion")
    current_theme.apply_theme(app)

    font = app.font()
    global_settings.ui_font_size and font.setPointSize(global_settings.ui_font_size)
    global_settings.ui_font_family and font.setFamily(global_settings.ui_font_family)
    app.setFont(font)

    main_windows = MainWindow()
    ToastNotifier(parent=main_windows)

    screen = app.screens()[0]
    screen_geometry = screen.availableGeometry()
    main_windows.resize(screen_geometry.width(), screen_geometry.height() * 0.75)
    main_windows.move(screen_geometry.left(), screen_geometry.top())
    main_windows.show()

    main_windows.showMaximized()

    # 先展示界面
    app.processEvents()

    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    kanban = KanBan(global_settings.metadata_directory, global_settings.resource_directory)
    main_windows.set_kanban(kanban)
    QApplication.restoreOverrideCursor()

    sys.exit(app.exec())




