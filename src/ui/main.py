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

from src.core.settings import settings
from src.core.kanban import Kanban
from src.ui.notifier import init_notifier
from src.ui.scan_archive_progress_dialog import ScanArchiveProgressDialog
from src.ui.main_window import MainWindow
from src.ui.color_theme import current_theme


if __name__ == "__main__":
    app = QApplication([])
    app.setWindowIcon(QIcon("./assets/icon.png"))

    QApplication.setStyle("Fusion")
    current_theme.apply_theme(app)

    # 设置字体
    font = app.font()
    settings.ui_font_size and font.setPointSize(settings.ui_font_size)
    settings.ui_font_family and font.setFamily(settings.ui_font_family)
    app.setFont(font)

    # 扫描 专辑归档 生成缓存
    scan_progress_dialog = ScanArchiveProgressDialog()
    if not scan_progress_dialog.scan_archive():
        app.quit()
        sys.exit(0)

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
    kanban = Kanban(settings.metadata_directory, settings.resource_directory)
    main_window.set_kanban(kanban)
    QApplication.restoreOverrideCursor()

    sys.exit(app.exec())




