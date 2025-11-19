from functools import wraps
from typing import Callable

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt


def with_busy_cursor(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
        if (cursor:= QApplication.overrideCursor()) and cursor.shape() == Qt.CursorShape.WaitCursor:
            return func(*args, **kwargs)
        
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            return func(*args, **kwargs)
        finally:
            QApplication.restoreOverrideCursor()
    return wrapper




