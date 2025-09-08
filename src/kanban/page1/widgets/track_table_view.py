import json
from typing import Any

from PySide6.QtCore import (QRect, QModelIndex, Qt, QAbstractItemModel, QObject, Signal, QMimeData,
                            QSize, )
from PySide6.QtGui import (QPainter, QDragEnterEvent, QDropEvent, QDragMoveEvent, QFont,
                           QFontMetrics, )
from PySide6.QtWidgets import (QFrame, QStyledItemDelegate, QWidget, QStyleOptionViewItem, QTableView, QHeaderView,
                               QAbstractItemView, )

from src.basemodels import Track
from src.kanban.kanban import ResourceState, AlbumKanBan
from src.kanban.theme_colors import current_theme
from src.kanban.page1.widgets.album_table_view import AlbumStateItemDelegate
from src.kanban.custom_table_item_model import CustomTableItemModel


class TrackTableItemModel(CustomTableItemModel):

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)

        self.headers = ["S", "TITLE"]
        self.col_cnt: int = len(self.headers)

    def set_album_kanban(self, album_kanban: AlbumKanBan = None) -> None:
        max_ms = 0b111111

        # 声明所有数据都无效，重新加载
        self.beginResetModel()
        
        if album_kanban:
            self.table = [[(rs, max_ms), (t.title, t.artist)]
                        for rs, t in zip(album_kanban.track_res_states, album_kanban.album.tracks)]
        else:
            self.table = []
        
        self.row_cnt = len(self.table)
        self.endResetModel()
    
    # 可编辑

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        # 资源状态列 只读
        if index.column() == 0:
            return Qt.ItemFlag.NoItemFlags
        
        return (Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDropEnabled)
    
    # drop 支持
    
    def supportedDropActions(self) -> Qt.DropAction:
        return Qt.DropAction.CopyAction | Qt.DropAction.MoveAction
    
    def canDropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int, parent: QModelIndex) \
            -> bool:
        return True


class TrackTitleItemDelegate(QStyledItemDelegate):

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()
        title, artist = index.data(Qt.ItemDataRole.DisplayRole)
        # 艺术家信息 增加缩进
        artist = " "*6 + artist
        rect: QRect = option.rect
        width: int = rect.width()
        font: QFont = option.font
        # 0.5 字符 行距
        title_rect = QRect(rect.left(), rect.top()+font.pixelSize()//2, rect.width(),
                           self._get_content_height(font, width, title))
        painter.drawText(title_rect, title)
        
        artist_rect = QRect(rect.left(), title_rect.bottom(), rect.width(),
                            self._get_content_height(font, width, artist))
        painter.setPen(current_theme.ARTIST_COLOR)
        painter.drawText(artist_rect, artist)
        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        title, artist = index.data(Qt.ItemDataRole.DisplayRole)
        artist = " "*6 + artist
        font: QFont = option.font
        width: int = option.rect.width()
        # 0.5 字符 行距
        height = (self._get_content_height(font, width, title) + self._get_content_height(font, width, artist)
                  + font.pixelSize())
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
        self.source_model = TrackTableItemModel()
        self.setModel(self.source_model)
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


