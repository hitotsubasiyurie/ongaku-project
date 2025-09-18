from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor


class DarkTheme:

    LOSSLESS_COLOR = QColor(46, 160, 67)
    LOSSY_COLOR = QColor(204, 153, 51)
    MISSING_COLOR = QColor(204, 204, 204)

    ARTIST_TEXT_COLOR = QColor(102, 102, 102)

    MARKED_BACKGROUND_COLOR = QColor(0, 0, 0)
    MARKED_FOREGROUND_COLOR = QColor(130, 130, 130)

    THEME_PROGRESS_COLL_COLOR = QColor(46, 160, 67, 50)
    THEME_PROGRESS_MARK_COLOR = QColor(70, 70, 70)

    def apply_theme(app: QApplication) -> None:
        dark_palette = QPalette()

        # 背景和窗口
        dark_palette.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
        dark_palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
        dark_palette.setColor(QPalette.ColorRole.Button, QColor(40, 40, 40))

        dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(224, 224, 224))
        dark_palette.setColor(QPalette.ColorRole.Text, QColor(224, 224, 224))
        # dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(224, 224, 224))

        # 高亮 同 VSCode
        dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(38, 79, 120, 150))

        app.setPalette(dark_palette)



current_theme = DarkTheme






