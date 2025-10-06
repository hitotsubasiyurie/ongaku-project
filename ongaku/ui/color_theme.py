from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor

from ongaku.core.settings import global_settings


class DarkTheme:

    NAME = "dark"

    LOSSLESS_COLOR = QColor(46, 160, 67)
    LOSSY_COLOR = QColor(204, 153, 51)
    PARTIAL_COLOR = QColor(231, 63, 63)
    MISSING_COLOR = QColor(204, 204, 204)

    MARKED_BACKGROUND_COLOR = QColor(0, 0, 0)
    MARKED_FOREGROUND_COLOR = QColor(130, 130, 130)

    THEME_PROGRESS_COLL_COLOR = QColor(51, 102, 51)
    THEME_PROGRESS_MARK_COLOR = QColor(80, 80, 80)

    def apply_theme(app: QApplication) -> None:
        dark_palette = QPalette()

        # 背景和窗口

        dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(245, 245, 245))
        dark_palette.setColor(QPalette.ColorRole.Text, QColor(224, 224, 224))
        dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(224, 224, 224))
        dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(224, 224, 224))
        dark_palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(160, 160, 160))

        dark_palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
        dark_palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
        dark_palette.setColor(QPalette.ColorRole.Button, QColor(40, 40, 40))

        dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(38, 79, 120))

        app.setPalette(dark_palette)


class LightTheme:

    NAME = "light"

    LOSSLESS_COLOR = QColor(46, 160, 67)
    LOSSY_COLOR = QColor(255, 204, 51)
    PARTIAL_COLOR = QColor(231, 63, 63)
    MISSING_COLOR = QColor(184, 184, 184)

    MARKED_BACKGROUND_COLOR = QColor(220, 220, 220)
    MARKED_FOREGROUND_COLOR = QColor(130, 130, 130)

    THEME_PROGRESS_COLL_COLOR = QColor(153, 204, 153)
    THEME_PROGRESS_MARK_COLOR = QColor(220, 220, 220)

    def apply_theme(app: QApplication) -> None:
        light_palette = QPalette()

        # 背景和窗口

        light_palette.setColor(QPalette.ColorRole.ButtonText, QColor(20, 20, 20))
        light_palette.setColor(QPalette.ColorRole.Text, QColor(30, 30, 30))
        light_palette.setColor(QPalette.ColorRole.WindowText, QColor(30, 30, 30))
        light_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(30, 30, 30))
        light_palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(60, 60, 60))

        light_palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        light_palette.setColor(QPalette.ColorRole.Window, QColor(248, 248, 248))
        light_palette.setColor(QPalette.ColorRole.Button, QColor(230, 230, 230))

        light_palette.setColor(QPalette.ColorRole.Highlight, QColor(173, 214, 255))

        app.setPalette(light_palette)


current_theme = next((t for t in [DarkTheme, LightTheme] if t.NAME == global_settings.ui_color_theme), DarkTheme)

