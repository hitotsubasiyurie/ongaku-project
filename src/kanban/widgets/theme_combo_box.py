from PySide6.QtCore import (Qt, QModelIndex, QRect, )
from PySide6.QtGui import (QColor, QPainter, QWheelEvent)
from PySide6.QtWidgets import (QWidget, QStyledItemDelegate, QStyleOptionViewItem, QComboBox, 
                               QListView, QStyle)


class CompletionDelegate(QStyledItemDelegate):

    def __init__(self, completions: dict[str, float], parent: QWidget = None):
        super().__init__(parent)
        self.theme2completions = completions
    
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:

        # 替换 item 状态
        option = QStyleOptionViewItem(option)
        option.state = QStyle.StateFlag.State_Enabled

        text = index.data()
        # 绘制 主题 完成进度
        if text in self.theme2completions:
            val = self.theme2completions[text]
            rect: QRect = option.rect
            comp_rect = QRect(rect.left(), rect.top(), int(rect.width() * val), rect.height())
            painter.fillRect(comp_rect, QColor(0xC1CAB7))
        super().paint(painter, option, index)


class ThemeComboBox(QComboBox):

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.theme2completions: dict[str, float] = None

        self.themes: list[str] = []

        # 设置默认文本
        self.setEditable(True)
        self.lineEdit().setText("")

        # 设置文本省略模式
        view = self.view()
        view.setTextElideMode(Qt.TextElideMode.ElideRight)

        # 取消监听 鼠标移动
        view.setMouseTracking(False)
        self.setMouseTracking(False)

        # 设置代理
        self.delegate = CompletionDelegate({})
        view.setItemDelegate(self.delegate)

        view.setSelectionMode(QListView.SelectionMode.NoSelection)

        self.activated.connect(self._on_activated)

    def set_themes(self, theme2completions: dict[str, float]) -> None:
        self.theme2completions = theme2completions
        self.delegate.theme2completions = theme2completions

        self.themes = list(theme2completions.keys())
        self._on_activated()

    # 重写方法

    def wheelEvent(self, e: QWheelEvent) -> None:
        # 禁用鼠标滚轮选择
        return None
    
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if not self.view().isVisible():
            self.showPopup()

    # 内部方法

    def _on_activated(self, *args) -> None:
        tmp = sorted(self.themes, key=lambda t: (t != self.currentText(), -1*self.theme2completions.get(t)))
        self.clear()
        self.addItems(tmp)

