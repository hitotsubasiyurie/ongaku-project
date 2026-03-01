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

from src.core.settings import g_settings
from src.core.kanban import Kanban
from src.gui.notify import init_notifier
from src.gui.main_window import MainWindow
from src.gui.color_theme import current_theme
from src.operations.health_check import health_check


if __name__ == "__main__":

    # 健康检查
    health_check()

    app = QApplication([])
    app.setWindowIcon(QIcon("./assets/icon.png"))

    QApplication.setStyle("Fusion")
    current_theme.apply_theme(app)

    # 设置字体
    font = app.font()
    g_settings.ui_font_size and font.setPointSize(g_settings.ui_font_size)
    g_settings.ui_font_family and font.setFamily(g_settings.ui_font_family)
    app.setFont(font)

    # 主窗口
    main_window = MainWindow()
    init_notifier(main_window)

    screen = app.screens()[0]
    screen_geometry = screen.availableGeometry()
    main_window.resize(screen_geometry.width(), screen_geometry.height() * 0.75)
    main_window.move(screen_geometry.left(), screen_geometry.top())
    main_window.show()

    main_window.showMaximized()
    app.processEvents()

    # 加载看板
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    kanban = Kanban(g_settings.metadata_directory, g_settings.resource_directory)
    main_window.set_kanban(kanban)
    QApplication.restoreOverrideCursor()

    sys.exit(app.exec())




