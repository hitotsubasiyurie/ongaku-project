import os
import sys
from pathlib import Path

# 指定运行目录
os.chdir(Path(__file__).parent.parent)

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from ongaku.core.settings import global_settings
from ongaku.core.kanban import KanBan
from ongaku.kanban_ui.init_settings_dialog import InitSettingsDialog
from ongaku.kanban_ui.toast_notifier import ToastNotifier
from ongaku.kanban_ui.page0.page0_widget import Page0Widget
from ongaku.kanban_ui.color_theme import current_theme


if __name__ == "__main__":
    app = QApplication([])
    app.setWindowIcon(QIcon("./kanban_ui/assets/icon.png"))

    QApplication.setStyle("Fusion")
    current_theme.apply_theme(app)

    font = app.font()
    global_settings.ui_font_size and font.setPointSize(global_settings.ui_font_size)
    global_settings.ui_font_family and font.setFamily(global_settings.ui_font_family)
    app.setFont(font)

    if not all([global_settings.metadata_directory, global_settings.resource_directory]):
        widget = InitSettingsDialog()
        result = widget.exec()
        if not result:
            app.quit()
            sys.exit(0)

    kanban = KanBan(global_settings.metadata_directory, global_settings.resource_directory)
    widget = Page0Widget()
    widget.set_kanban(kanban)
    ToastNotifier(parent=widget)

    screen = app.screens()[0]
    screen_geometry = screen.availableGeometry()
    width = screen_geometry.width()
    height = int(screen_geometry.height() * 0.75)
    widget.resize(width, height)
    widget.move(screen_geometry.left(), screen_geometry.top())
    widget.show()

    widget.showMaximized()

    sys.exit(app.exec())




