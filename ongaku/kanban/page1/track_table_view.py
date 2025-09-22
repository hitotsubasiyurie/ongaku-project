import json
from typing import Any

from PySide6.QtCore import QRect, QModelIndex, Qt, QObject, Signal, QMimeData, QSize
from PySide6.QtGui import QPainter, QDragEnterEvent, QDropEvent, QFont, QFontMetrics, QBrush
from PySide6.QtWidgets import (QFrame, QStyledItemDelegate, QWidget, QStyleOptionViewItem, QTableView, 
    QHeaderView, QAbstractItemView, QStyle)

from ongaku.kanban.kanban import AlbumKanBan
from ongaku.kanban.ui_theme import current_theme
from ongaku.kanban.page1.album_table_view import AlbumStateItemDelegate
from ongaku.kanban.widgets.custom_table_item_model import CustomTableItemModel


class TrackTableItemModel(CustomTableItemModel):

    MARKED_QBRUSHES = {
        Qt.ItemDataRole.BackgroundRole: QBrush(current_theme.MARKED_BACKGROUND_COLOR),
        Qt.ItemDataRole.ForegroundRole: QBrush(current_theme.MARKED_FOREGROUND_COLOR)
    }

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)

        self.headers = ["S", "TITLE"]
        self.col_cnt: int = len(self.headers)

        self.album_kanban: AlbumKanBan = None

        self.track_marks: list[bool] = []

    def reset_album_kanban(self, album_kanban: AlbumKanBan = None) -> None:
        ms = 0b111110

        # 声明重置模型
        self.beginResetModel()
        
        # 重置数据
        self.album_kanban = album_kanban
        self.track_marks = []
        self.table = []
        # 默认 以 S 列 排序
        self.sort_args = (0, Qt.SortOrder.AscendingOrder)
        self.filters = {}

        if album_kanban:
            self.table = [[(rs, ms | bool(t.artist)), (t.title, t.artist)]
                        for rs, t in zip(album_kanban.track_res_states, album_kanban.album.tracks)]
            self.track_marks = [bool(t.mark) for t in album_kanban.album.tracks]

        self.layout_ps = list(range(len(self.table)))
        # 应用排序
        self._apply_sort()
        self.layout_row = len(self.layout_ps)

        self.endResetModel()

    def data(self, index: QModelIndex, role: Qt.ItemDataRole = None) -> Any:
        row, col = index.row(), index.column()

        if not index.isValid() or row >= self.layout_row or col >= self.col_cnt:
            return None
        
        # 已有 Mark 信息 置灰
        if self.track_marks[self.layout_ps[row]] and role in self.MARKED_QBRUSHES:
            return self.MARKED_QBRUSHES[role]
        
        return super().data(index, role)

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        # S 列 只读
        if index.column() == 0:
            return Qt.ItemFlag.NoItemFlags
        
        return (Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDropEnabled)
    
    def setData(self, index: QModelIndex, value: Any, role: Qt.ItemDataRole = Qt.ItemDataRole.EditRole) -> bool:
        row, col = index.row(), index.column()

        if not index.isValid() or row >= self.layout_row or col >= self.col_cnt:
            return False
        
        # 仅响应 EditRole
        if role != Qt.ItemDataRole.EditRole:
            return False

        # 仅响应 TITLE 列
        if col != 1:
            return False
        
        # 转元组
        value = tuple(json.loads(str(value)))

        p = self.layout_ps[row]

        # 值不变时不更新视图
        if self.table[p][col] == value:
            return False
    
        # 更新数据
        self.table[p][col] = value
        self.album_kanban.album.tracks[p].title = value[0]
        self.album_kanban.album.tracks[p].artist = value[1]

        # 刷新视图
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole])
        return True

    # drop 支持
    
    def supportedDropActions(self) -> Qt.DropAction:
        return Qt.DropAction.CopyAction | Qt.DropAction.MoveAction
    
    def canDropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int, parent: QModelIndex) \
            -> bool:
        return True


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

    # 重写方法

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        # 激活窗口
        self.activateWindow()
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        self.paths_dropped.emit(paths)
        event.acceptProposedAction()


