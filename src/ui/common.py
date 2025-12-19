from functools import wraps
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


BUTTON_QSS = """
QPushButton {{
    /* 透明背景 */
    background-color: rgba(100, 100, 100, 0);
    /* 50% 圆角 */
    border-radius: {}px;
}}

QPushButton:hover {{
    /* 悬浮 */
    background-color: rgba(100, 100, 100, 200);
}}
"""


def with_busy_cursor(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
        cursor = QApplication.overrideCursor()
        pushed = False

        if not (cursor and cursor.shape() == Qt.CursorShape.WaitCursor):
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            pushed = True

        try:
            return func(*args, **kwargs)
        finally:
            if pushed:
                QApplication.restoreOverrideCursor()
    
    return wrapper




