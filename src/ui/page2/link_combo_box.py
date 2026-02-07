import webbrowser
from typing import Optional

from PySide6.QtCore import (Qt, Signal)
from PySide6.QtGui import (QWheelEvent, )
from PySide6.QtWidgets import (QWidget, QComboBox, )

from src.core.i18n import MESSAGE
from src.core.kanban import AlbumKanBan

class LinkComboBox(QComboBox):

    link_added = Signal()

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.album_kanban: Optional[AlbumKanBan] = None

        # 设置默认文本
        self.setEditable(True)
        self.lineEdit().clear()

        # 设置文本省略模式
        view = self.view()
        view.setTextElideMode(Qt.TextElideMode.ElideRight)

        # 取消监听 鼠标移动
        view.setMouseTracking(False)
        self.setMouseTracking(False)

        self.activated.connect(self._on_activated)
        self.lineEdit().returnPressed.connect(self._on_return_pressed)

    def set_album_kanban(self, album_kanban: AlbumKanBan | None) -> None:
        self.album_kanban = album_kanban
        self._set_items()

    # 重写方法

    def wheelEvent(self, e: QWheelEvent) -> None:
        # 禁用鼠标滚轮选择
        return None
    
    # 内部方法

    def _set_items(self) -> None:
        links = self.album_kanban.album.links
        self.clear()
        self.addItems(links)
        self.lineEdit().clear()
        self.lineEdit().setPlaceholderText(MESSAGE.UI_20251231_180009.format(len(links)))

    # 事件动作

    def _on_activated(self, index: int) -> None:
        webbrowser.open(self.album_kanban.album.links[index])
        self.lineEdit().clear()

    def _on_return_pressed(self) -> None:
        text = self.lineEdit().text().strip()
        self.lineEdit().clear()

        if not text or text in self.album_kanban.album.links:
            return
        
        self.album_kanban.album.links = self.album_kanban.album.links + (text, )
        self._set_items()
        self.link_added.emit()

