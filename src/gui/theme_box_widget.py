from PySide6.QtCore import (Qt, QObject, QEvent, Signal, )
from PySide6.QtGui import (QColor, QFocusEvent, )
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, QListWidget, QAbstractScrollArea, QListWidgetItem, )


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

        self.themes: list[str] = []
        self.current: list[str] = []
        self.selected: list[str] = []

        self.setup_ui()

    def set_themes(self, themes: list[str]) -> None:
        self.themes = themes
        self._update_list_items()

    def set_current_themes(self, current: list[str]) -> None:
        self.current = current
        self._update_list_items()

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
        # list_widget 展示优先级 selected > current > themes
        tmp = list(dict.fromkeys(self.selected + self.current + self.themes))
        self.list_widget.clear()
        self.list_widget.addItems(tmp)
        # 设置 背景颜色
        for i, t in enumerate(tmp):
            if t in self.selected:
                self.list_widget.item(i).setBackground(QColor(0x6699CC))
            elif t in self.current:
                self.list_widget.item(i).setBackground(QColor(0xDAE2FF))
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
        text = item.text()
        self.selected.remove(text) if text in self.selected else self.selected.append(text)
        self._update_list_items()
        # 发出信号
        self.selected_changed.emit()

    def _show_list_widget(self) -> None:
        pos = self.mapToGlobal(self.line_edit.geometry().bottomLeft())
        self.list_widget.move(pos)
        self.list_widget.show()
        # 展示后 再减去 滚动条宽度
        self.list_widget.setFixedWidth(self.width()-self.list_widget.verticalScrollBar().width())












