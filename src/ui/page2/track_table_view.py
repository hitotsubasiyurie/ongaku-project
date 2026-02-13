import json
from typing import Any, Optional

from PySide6.QtCore import QRect, QModelIndex, Qt, QObject, Signal, QMimeData, QSize
from PySide6.QtGui import QPainter, QDragEnterEvent, QDropEvent, QFont, QFontMetrics, QBrush, QAction
from PySide6.QtWidgets import (QFrame, QStyledItemDelegate, QWidget, QStyleOptionViewItem, QTableView,
                               QHeaderView, QAbstractItemView, QStyle)

from src.core.kanban import AlbumKanban
from src.core.i18n import MESSAGE
from src.ui.color_theme import current_theme
from src.ui.custom.custom_table_item_model import CustomTableItemModel
from src.ui.page2.album_table_view import AlbumStateItemDelegate


class TrackTableItemModel(CustomTableItemModel):

    MARKED_BACKGROUND_QBRUSHES = QBrush(current_theme.MARKED_BACKGROUND_COLOR)
    MARKED_FOREGROUND_QBRUSHES = QBrush(current_theme.MARKED_FOREGROUND_COLOR)

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)

        self.headers: list[str] = ["S", MESSAGE.UI_20260101_112210]

        self.album_kanban: Optional[AlbumKanban] = None

    def reset_album_kanban(self, album_kanban: AlbumKanban = None) -> None:
        # 声明重置模型
        self.beginResetModel()
        
        # 重置数据
        self.album_kanban = album_kanban
        self.layout_ps = list(range(len(self.album_kanban.album.tracks))) if album_kanban else []

        # 默认 以 S 列 排序
        self.sort_args = (0, Qt.SortOrder.AscendingOrder)
        # 清空筛选
        self.filters = {}

        # 应用排序
        self._apply_sort()

        self.endResetModel()

    def data(self, index: QModelIndex, role: Qt.ItemDataRole = None) -> Any:
        row, col = index.row(), index.column()

        if not index.isValid() or row >= len(self.layout_ps) or col >= len(self.headers):
            return None
        
        p = self.layout_ps[row]

        # 前景
        if role == Qt.ItemDataRole.ForegroundRole:
            # 已有 Mark 信息
            if self.album_kanban.album.tracks[p].mark:
                return self.MARKED_FOREGROUND_QBRUSHES
 
        # 背景
        if role == Qt.ItemDataRole.BackgroundRole:
            # 已有 Mark 信息
            if self.album_kanban.album.tracks[p].mark:
                return self.MARKED_BACKGROUND_QBRUSHES

        # DisplayRole, EditRole
        if role in [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]:
            return self._get_data(col, p)

        return None

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole) -> Any:

        if role == Qt.ItemDataRole.TextAlignmentRole and orientation == Qt.Orientation.Vertical:
            return Qt.AlignmentFlag.AlignLeft

        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Vertical:
            if self.album_kanban.album.tracks[self.layout_ps[section]].mark == "1":
                return f"🤍"

        return super().headerData(section, orientation, role)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        # S 列 只读
        if index.column() == 0:
            return Qt.ItemFlag.NoItemFlags
        
        # 允许 拖入
        return (Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDropEnabled)
    
    def setData(self, index: QModelIndex, value: Any, role: Qt.ItemDataRole = Qt.ItemDataRole.EditRole) -> bool:
        row, col = index.row(), index.column()

        if not index.isValid() or row >= len(self.layout_ps) or col >= len(self.headers):
            return False

        # 仅响应 EditRole
        if role != Qt.ItemDataRole.EditRole:
            return False

        # 转元组
        value = tuple(json.loads(str(value)))

        # 更新数据
        p = self.layout_ps[row]
        old_hash = hash(self.album_kanban.album)

        if col == 1:
            self.album_kanban.album.tracks[p].title = value[0]
            self.album_kanban.album.tracks[p].artist = value[1]

        if old_hash == hash(self.album_kanban.album):
            return False

        # 刷新视图
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])
        return True

    # drop 支持
    
    def supportedDropActions(self) -> Qt.DropAction:
        return Qt.DropAction.CopyAction | Qt.DropAction.MoveAction
    
    def canDropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int, parent: QModelIndex) \
            -> bool:
        return True

    # 内部方法

    def _get_data(self, col: int, p: int) -> str:
        ms = 0b111110

        if col == 0:
            return (self.album_kanban.track_resource_states[p], 
                    ms | bool(self.album_kanban.album.tracks[p].artist))
        elif col == 1:
            return (self.album_kanban.album.tracks[p].title, 
                    self.album_kanban.album.tracks[p].artist)


class TrackTitleItemDelegate(QStyledItemDelegate):

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        # 绘制背景
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        elif (bg := index.data(Qt.ItemDataRole.BackgroundRole)):
            painter.fillRect(option.rect, QBrush(bg))

        painter.save()

        # 前景颜色
        if fg:= index.data(Qt.ItemDataRole.ForegroundRole):
            painter.setPen(fg.color())

        title, artist = index.data(Qt.ItemDataRole.DisplayRole)
        # 艺术家信息 增加缩进
        artist = " "*6 + artist
        rect: QRect = option.rect
        width: int = rect.width()
        font: QFont = option.font
        fh = QFontMetrics(font).height()
        # 0.5 字符 行距
        title_rect = QRect(rect.left(), rect.top()+fh//4, rect.width(),
                           self._get_content_height(font, width, title))
        painter.drawText(title_rect, title)
        
        artist_rect = QRect(rect.left(), title_rect.bottom()+fh//4, rect.width(),
                            self._get_content_height(font, width, artist))
        painter.setPen(current_theme.MARKED_FOREGROUND_COLOR)
        # artist 字体减小
        font.setPointSize(font.pointSize() - 1)
        painter.setFont(font)
        painter.drawText(artist_rect, artist)
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        title, artist = index.data(Qt.ItemDataRole.DisplayRole)
        artist = " "*6 + artist
        font: QFont = option.font
        fh = QFontMetrics(font).height()
        width: int = option.rect.width()
        # 0.5 字符 行距
        height = (self._get_content_height(font, width, title) + self._get_content_height(font, width, artist)
                  + fh//2)
        return QSize(width, height)

    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        # 被编辑时，展示 json 格式化内容
        editor.setText(json.dumps(index.data(Qt.ItemDataRole.DisplayRole), ensure_ascii=False))

    # 内部方法

    @staticmethod
    def _get_content_height(font: QFont, width: int, text: str) -> int:
        metrics = QFontMetrics(font)
        height = metrics.boundingRect(QRect(0, 0, width, 0), Qt.TextFlag.TextWordWrap, text).height()
        return height


class TrackTableView(QTableView):

    paths_dropped = Signal(list)
    action_copy_filename_clicked = Signal()

    def setup_context_menu(self) -> None:
        """初始化 右键菜单"""
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        action = QAction(MESSAGE.UI_20260101_112231, self)
        action.triggered.connect(self.action_copy_filename_clicked.emit)
        self.addAction(action)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        # 初始化模型
        self.item_model = TrackTableItemModel()
        self.setModel(self.item_model)
        self.setItemDelegateForColumn(0, AlbumStateItemDelegate(self))
        self.setItemDelegateForColumn(1, TrackTitleItemDelegate(self))

        # 表格无边框
        self.setShowGrid(False)
        self.setFrameShape(QFrame.Shape.NoFrame)
        # 可编辑
        self.setEditTriggers(QTableView.EditTrigger.DoubleClicked)
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        # 条目滚动 提高性能
        self.setVerticalScrollMode(QTableView.ScrollMode.ScrollPerItem)
        # 允许拖入
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setDropIndicatorShown(True)

        # 字体高度
        fh = self.fontMetrics().height()

        # 设置行
        header = self.verticalHeader()
        header.setSectionsClickable(False)
        # 行高使用 sizeHint
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setFrameShape(QFrame.Shape.NoFrame)
        
        # 设置列
        header = self.horizontalHeader()
        column_size = [fh*1.5, 0]
        [self.setColumnWidth(i, w) for i, w in enumerate(column_size)]
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionsClickable(False)

        self.setup_context_menu()

    def get_selected_ps(self) -> list[int]:
        # selectedIndexes 以索引为单位，一行多个
        rows = list(sorted(set(i.row() for i in self.selectedIndexes())))
        # 原始数据行指针
        ps = [self.item_model.layout_ps[r] for r in rows]
        return ps

    # 重写方法

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        # 激活窗口
        self.activateWindow()
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        self.paths_dropped.emit(paths)
        event.acceptProposedAction()


