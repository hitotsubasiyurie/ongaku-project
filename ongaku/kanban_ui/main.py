import os
import sys
from pathlib import Path

executable = Path(sys.argv[0])
# 指定运行目录 当前父目录
os.chdir(executable.parent)

# 若是源码运行 添加导包路径
if executable.suffix == ".py":
    sys.path[0] = str(executable.parent.parent.parent)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt

from ongaku.core.settings import global_settings
from ongaku.core.kanban import KanBan
from ongaku.kanban_ui.toast_notifier import ToastNotifier
from ongaku.kanban_ui.page0.page0_widget import Page0Widget
from ongaku.kanban_ui.color_theme import current_theme


if __name__ == "__main__":
    app = QApplication([])
    app.setWindowIcon(QIcon("./assets/icon.png"))

    QApplication.setStyle("Fusion")
    current_theme.apply_theme(app)

    font = app.font()
    global_settings.ui_font_size and font.setPointSize(global_settings.ui_font_size)
    global_settings.ui_font_family and font.setFamily(global_settings.ui_font_family)
    app.setFont(font)

    widget = Page0Widget()
    ToastNotifier(parent=widget)

    screen = app.screens()[0]
    screen_geometry = screen.availableGeometry()
    width = screen_geometry.width()
    height = int(screen_geometry.height() * 0.75)
    widget.resize(width, height)
    widget.move(screen_geometry.left(), screen_geometry.top())
    widget.show()

    widget.showMaximized()

    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    kanban = KanBan(global_settings.metadata_directory, global_settings.resource_directory)
    widget.set_kanban(kanban)
    QApplication.restoreOverrideCursor()

    sys.exit(app.exec())




