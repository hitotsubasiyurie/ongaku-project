from PySide6.QtCore import (Qt, QObject, QEvent, Signal, QModelIndex, QRect, )
from PySide6.QtGui import (QColor, QFocusEvent, QPainter, )
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, QListWidget, QAbstractScrollArea, QListWidgetItem, 
    QStyledItemDelegate, QStyleOptionViewItem, )


class CompletionDelegate(QStyledItemDelegate):

    def __init__(self, completions: dict[str, float], parent: QWidget = None):
        super().__init__(parent)
        self.theme2completions = completions
    
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        text = index.data()[1:]
        if text in self.theme2completions:
            val = self.theme2completions[text]
            rect: QRect = option.rect
            comp_rect = QRect(rect.left(), rect.top(), int(rect.width() * val), rect.height())
            painter.fillRect(comp_rect, QColor(0xC1CAB7))
        super().paint(painter, option, index)

class ThemeBoxWidget(QWidget):

    selected_changed = Signal()

    def setup_ui(self):
        # 初始化 UI
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.line_edit = QLineEdit()
        layout.addWidget(self.line_edit)
        self.line_edit.installEventFilter(self)
        self.line_edit.textEdited.connect(self._on_line_edit_text_changed)

        self.list_widget = QListWidget(self)
        self.delegate = CompletionDelegate([])
        self.list_widget.setItemDelegate(self.delegate)
        # 设置 弹出 非模态不阻塞
        self.list_widget.setWindowFlag(Qt.WindowType.FramelessWindowHint | Qt.WindowType.ToolTip)
        self.list_widget.setWindowModality(Qt.WindowModality.NonModal)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # 自适应高度
        self.list_widget.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        # 最大高度 40 行
        self.list_widget.setMaximumHeight(self.font().pixelSize()*40)
        self.list_widget.itemDoubleClicked.connect(self._on_list_item_clicked)
        self.list_widget.hide()

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.theme2completions: dict[str, float] = {}

        self.themes: list[str] = []
        self.selected_theme: str = None

        self.setup_ui()

    def set_themes(self, theme2completions: dict[str, float]) -> None:
        self.theme2completions = theme2completions
        self.delegate.theme2completions = theme2completions

        self.themes = list(theme2completions.keys())
        self.selected_theme = None

        self._update_list_items()

        # 发出信号
        self.selected_changed.emit()

    # 重写方法

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        # line_edit 被点击时 弹出 list_widget
        if watched == self.line_edit and event.type() == QEvent.Type.MouseButtonRelease:
            self.list_widget.isHidden() and self._show_list_widget()
        # 所有部件失去焦点时，隐藏 list_widget
        if event.type() == QEvent.Type.FocusOut:
            if not any([self.line_edit.hasFocus(), self.list_widget.hasFocus(), self.hasFocus()]):
                not self.list_widget.isHidden() and self.list_widget.hide()
        # 继续执行父类逻辑
        return super().eventFilter(watched, event)

    # 内部方法

    def _update_list_items(self) -> None:
        # list_widget 展示优先级 selected > themes
        tmp = sorted(self.themes, key=lambda t: (t != self.selected_theme, -1*self.theme2completions.get(t)))
        # 等宽 空白字符
        tmp = [f"⚫{t}" if t == self.selected_theme else f"　{t}" for t in tmp]
        self.list_widget.clear()
        self.list_widget.addItems(tmp)
        # 滚动 list_widget 至顶
        self.list_widget.scrollToTop()
        self._hide_list_items()

    def _hide_list_items(self, *args, **kwargs) -> None:
        # 根据 line_edit 内容，展示/隐藏 list_widget 元素
        text = self.line_edit.text().lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(text not in item.text().lower())

    def _on_line_edit_text_changed(self, text: str) -> None:
        # line_edit 被编辑时，展示 list_widget
        self.list_widget.isHidden() and self._show_list_widget()
        self._hide_list_items()

    def _on_list_item_clicked(self, item: QListWidgetItem) -> None:
        # list_widget 元素被双击时，选择/取消选择 元素
        text = item.text()[1:]
        if self.selected_theme == text:
            self.selected_theme = None
        else:
            self.selected_theme = text
        self._update_list_items()
        # 发出信号
        self.selected_changed.emit()

    def _show_list_widget(self) -> None:
        pos = self.mapToGlobal(self.line_edit.geometry().bottomLeft())
        self.list_widget.move(pos)
        self.list_widget.show()
        # 展示后 再减去 滚动条宽度
        self.list_widget.setFixedWidth(self.width()-self.list_widget.verticalScrollBar().width())












