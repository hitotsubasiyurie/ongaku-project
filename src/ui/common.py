from functools import wraps
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


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




