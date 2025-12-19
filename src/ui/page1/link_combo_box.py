import webbrowser

from PySide6.QtCore import (Qt, )
from PySide6.QtGui import (QWheelEvent, )
from PySide6.QtWidgets import (QWidget, QComboBox, )


class LinkComboBox(QComboBox):

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.links = []

        # 设置默认文本
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.lineEdit().setText("")

        # 设置文本省略模式
        view = self.view()
        view.setTextElideMode(Qt.TextElideMode.ElideRight)

        # 取消监听 鼠标移动
        view.setMouseTracking(False)
        self.setMouseTracking(False)

        self.activated.connect(self._open_link)

    def set_links(self, links: list[str]) -> None:
        self.links = links
        self.clear()
        self.addItems(links)
        self.lineEdit().setText(f"{len(self.links)} links")

    ######## 重写方法 ########

    def wheelEvent(self, e: QWheelEvent) -> None:
        # 禁用鼠标滚轮选择
        return None

    ######## 内部方法 ########

    def _open_link(self, index: int) -> None:
        webbrowser.open(self.links[index])
        self.lineEdit().setText(f"{len(self.links)} links")


