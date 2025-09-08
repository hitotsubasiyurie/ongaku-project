from PySide6.QtCore import (Qt, QObject, QEvent, Signal, QModelIndex, QRect, QSize, )
from PySide6.QtGui import (QFocusEvent, QPainter, QFocusEvent, )
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, QListWidget, QAbstractScrollArea, QListWidgetItem, 
    QStyledItemDelegate, QStyleOptionViewItem, QStyle, )

from src.kanban.kanban import KanBan
from src.kanban.theme_colors import current_theme


class ProgressDelegate(QStyledItemDelegate):

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self.fh = None
        self.coll_dict: dict[str, float] = {}
        self.mark_dict: dict[str, float] = {}

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:

        # 替换 item 状态
        option = QStyleOptionViewItem(option)
        option.state = QStyle.StateFlag.State_Enabled
        
        text = index.data()[2:]
        rect: QRect = option.rect

        painter.save()

        if text in self.coll_dict:
            val = self.coll_dict[text]
            w = int(rect.width() * val)
            comp_rect = QRect(rect.left(), rect.top(), w, rect.height())
            painter.fillRect(comp_rect, current_theme.THEME_PROGRESS_COLL_COLOR)

        if text in self.mark_dict:
            val = self.mark_dict[text]
            w = int(rect.width() * val)
            comp_rect = QRect(rect.left(), rect.top(), w, rect.height())
            painter.fillRect(comp_rect, current_theme.THEME_PROGRESS_MARK_COLOR)

        painter.restore()

        super().paint(painter, option, index)

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        # 1.5 倍高度
        size = super().sizeHint(option, index)
        size.setHeight(self.fh*1.5)
        return size


class ThemeBoxWidget(QWidget):

    selected_changed = Signal()

    def setup_ui(self):
        # 字体高度
        fh = self.fontMetrics().height()
        self.setFixedWidth(fh*32)

        # 初始化 UI
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.line_edit = QLineEdit(self)
        self.line_edit.setFixedHeight(fh*1.5)
        layout.addWidget(self.line_edit)
        self.line_edit.textEdited.connect(self._on_line_edit_text_changed)

        self.list_widget = QListWidget(self)
        self.delegate = ProgressDelegate()
        self.delegate.fh = fh
        self.list_widget.setItemDelegate(self.delegate)
        layout.addWidget(self.list_widget)

        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # 自适应高度
        self.list_widget.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.list_widget.itemDoubleClicked.connect(self._on_list_item_clicked)

        # 弹出窗口类型
        self.setWindowFlags(Qt.WindowType.Popup)
        
    
    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.theme_names: list[str] = []
        self.selected_theme: str = None

        self.setup_ui()

    def set_kanban(self, kanban: KanBan) -> None:
        self.theme_names = [k.theme_name for k in kanban.theme_kanbans]
        self.coll_dict = {k.theme_name: k.collection_progress for k in kanban.theme_kanbans}
        self.mark_dict = {k.theme_name: k.mark_progress for k in kanban.theme_kanbans}

        self.delegate.coll_dict = self.coll_dict
        self.delegate.mark_dict = self.mark_dict

        self._update_list_items()

    # 内部方法

    def _update_list_items(self) -> None:
        # list_widget 展示优先级 selected > themes
        tmp = sorted(self.theme_names, key=lambda t: (t != self.selected_theme, -1*self.coll_dict.get(t), self.mark_dict.get(t)))
        # 等宽 空白字符 两个字符
        tmp = [f"⚪️{t}" if t == self.selected_theme else f"　　{t}" for t in tmp]
        self.list_widget.clear()
        self.list_widget.addItems(tmp)
        # 滚动 list_widget 至顶
        self.list_widget.scrollToTop()
        self._hide_list_items()

        # 字体高度
        fh = self.fontMetrics().height()
        self.list_widget.setFixedHeight(min(len(tmp), 10)*fh*1.75)
        self.adjustSize()

    def _hide_list_items(self, *args, **kwargs) -> None:
        # 根据 line_edit 内容，展示/隐藏 list_widget 元素
        text = self.line_edit.text().lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(text not in item.text().lower())

    def _on_line_edit_text_changed(self, text: str) -> None:
        self._hide_list_items()

    def _on_list_item_clicked(self, item: QListWidgetItem) -> None:
        # 双击后 隐藏窗口
        self.hide()
        # list_widget 元素被双击时，选择/取消选择 元素
        text = item.text()[2:]
        if self.selected_theme == text:
            self.selected_theme = None
        else:
            self.selected_theme = text
        self._update_list_items()
        # 发出信号
        self.selected_changed.emit()












