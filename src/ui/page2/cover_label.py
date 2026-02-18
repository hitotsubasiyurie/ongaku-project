import itertools
from io import BytesIO
from typing import Optional
from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt, QEvent, QObject, Signal, QByteArray, QBuffer
from PySide6.QtGui import (QPixmap, QPainter, QColor, QPaintEvent, QBrush, QShortcut, QKeySequence,
                           QGuiApplication, QFont)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget

from src.core.i18n import MESSAGE
from src.core.kanban import AlbumKanban, MetadataState
from src.ui.common import with_busy_cursor
from src.ui.notifier import show_toast_msg
from src.utils import convert_to_png

OPACITY_CYCLE = itertools.cycle([0.2, 1, 0])


class CoverLabel(QLabel):

    image_pasted = Signal(bytes)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.album_kanban: Optional[AlbumKanban] = None
        # 封面
        self.pix: Optional[QPixmap] = None
        # 缩放的封面
        self.scaled_pix: Optional[QPixmap] = None
        # 封面信息
        self.image_info: Optional[str] = None

        # 透明效果
        self.opacity: Optional[float] = None
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        # 控件在最上层
        self.raise_()
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        self.change_opacity()

        # 监听父类大小变化
        parent.installEventFilter(self)

        # 快捷键
        QShortcut(QKeySequence("Ctrl+V"), self, activated=self._on_image_pasted)

    def set_album_kanban(self, album_kanban: AlbumKanban | None) -> None:
        self.album_kanban = album_kanban
        self.pix, self.scaled_pix, self.image_info = None, None, None

        # 不/半透明时 加载封面
        if album_kanban and (album_kanban.metadata_state & MetadataState.COVER_EXIST) and self.opacity:
            self._load_cover()

        self._set_geometry()

        self.update()

    def change_opacity(self) -> None:
        self.opacity = next(OPACITY_CYCLE)

        self.opacity_effect.setOpacity(self.opacity)

        # 不透明时 拦截鼠标事件，半/透明时 鼠标事件透传
        if self.opacity == 1:
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        else:
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        # 切换 不/半透明时 加载封面
        if self.album_kanban and (self.album_kanban.metadata_state & MetadataState.COVER_EXIST) and self.opacity and self.pix is None:
            self._load_cover()
            self._set_geometry()

        self.update()
        show_toast_msg(MESSAGE.UI_20251224_210500.format(self.opacity))

    # 重写方法

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        # 父控件大小变化时，更新布局
        if obj == self.parent():
            if event.type() in (QEvent.Type.Resize, QEvent.Type.Move):
                self._set_geometry()
        return super().eventFilter(obj, event)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)

        if not self.album_kanban:
            return
        
        margin = 5
        text_rect = self.rect().adjusted(margin, margin, -margin, -margin)
        painter = QPainter(self)

        # 有封面 不透明 时
        if self.pix and self.opacity == 1:
            painter.drawPixmap(0, 0, self.scaled_pix)

            font = painter.font()
            font.setPointSize(font.pointSize() + 2)
            text_flags = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap

            painter.setPen(Qt.GlobalColor.white)
            font.setWeight(QFont.Weight.Black)
            painter.setFont(font)
            painter.drawText(text_rect, text_flags, self.image_info)

            painter.setPen(Qt.GlobalColor.black)
            font.setWeight(QFont.Weight.Thin)
            painter.setFont(font)
            painter.drawText(text_rect, text_flags, self.image_info)

        # 无封面 不透明 时
        elif not self.pix and self.opacity == 1:
            painter.fillRect(self.rect(), QColor(200, 200, 200))
            brush = QBrush(QColor(100, 100, 100), Qt.BrushStyle.FDiagPattern)
            painter.fillRect(self.rect(), brush)

            painter.setPen(Qt.GlobalColor.black)
            font = painter.font()
            font.setPointSize(font.pointSize() + 2)
            painter.setFont(font)
            painter.drawText(text_rect, 
                             Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, 
                             "Ctrl + V to paste image")

        # 有封面 半透明 时
        elif self.pix and self.opacity == 0.2:
            painter.drawPixmap(0, 0, self.scaled_pix)

        # 其余情况
        else:
            # 空白
            pass

    # 内部方法

    @with_busy_cursor
    def _load_cover(self) -> None:
        self.pix = QPixmap()
        self.scaled_pix = None
        cover_bytes = self.album_kanban.read_path_bytes(self.album_kanban.cover_path)
        self.pix.loadFromData(cover_bytes)

        # Image.open 是惰性操作
        with Image.open(BytesIO(cover_bytes)) as img:
            info = {"format": img.format, 
                    "mode": img.mode, "resolution": img.size, 
                    "file_size": "{:.2f} MiB".format(len(cover_bytes) / 1024 / 1024)}

        _len = max(map(len, info.keys()))
        self.image_info = "\n".join(f"{k.ljust(_len)}: {v}" for k, v in info.items())

    def _set_geometry(self) -> None:
        parent: QWidget = self.parent()

        if self.pix:
            # 仅在需要时缩放封面
            if not self.scaled_pix or (self.scaled_pix.width() != parent.width() and self.scaled_pix.height() != parent.height()):
                self.scaled_pix = self.pix.scaled(parent.size(), 
                                                Qt.AspectRatioMode.KeepAspectRatio, 
                                                Qt.TransformationMode.SmoothTransformation)
            self.resize(self.scaled_pix.size())
        else:
            l = min(parent.size().toTuple())
            self.resize(l, l)

        # 坐标是相对于父类的
        x = parent.width() - self.width()
        y = parent.height() - self.height()
        self.move(x, y)

    # 事件动作

    @with_busy_cursor
    def _on_image_pasted(self) -> None:
        # 半/透明时 跳过
        if not self.opacity == 1:
            return
        
        img = QGuiApplication.clipboard().image()
        if img.isNull():
            return
        img.bits()
        ba = QByteArray()
        buffer = QBuffer(ba)
        buffer.open(QBuffer.OpenModeFlag.WriteOnly)
        img.save(buffer, "PNG")
        self.image_pasted.emit(bytes(ba))
