import os
import itertools
from PIL import Image

from PySide6.QtCore import Qt, QEvent, QObject, Signal, QByteArray, QBuffer
from PySide6.QtGui import (QPixmap, QPainter, QColor, QPaintEvent, QBrush, QShortcut, QKeySequence, 
    QGuiApplication, QFont)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget

from ongaku.core.kanban import AlbumKanBan
from ongaku.ui.toast_notifier import toast_notify
from ongaku.ui.common import with_busy_cursor


OPACITY_CYCLE = itertools.cycle([0.2, 1, 0])


class CoverLabel(QLabel):

    image_pasted = Signal(bytes)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.album_kanban: AlbumKanBan = None
        # 封面
        self.pix: QPixmap = None
        # 缩放的封面
        self.scaled_pix: QPixmap = None
        # 封面信息
        self.image_info: str = None

        # 透明效果
        self.opacity: float = None
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        self.raise_()
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        self.change_opacity()

        # 监听父类大小变化
        parent.installEventFilter(self)

        # 快捷键
        QShortcut(QKeySequence("Ctrl+V"), self, activated=self._on_image_pasted)

    @with_busy_cursor
    def set_album_kanban(self, album_kanban: AlbumKanBan | None) -> None:
        self.album_kanban = album_kanban

        # 无封面时
        if not album_kanban or not (cover:= album_kanban.cover):
            self.pix, self.scaled_pix, self.image_info = None, None, None

        # 有封面时
        else:
            self.pix = QPixmap(cover)
            self.scaled_pix = None

            with Image.open(cover) as img:
                info = {"filename": os.path.basename(cover), "format": img.format, "mode": img.mode, "resolution": img.size, 
                        "file_size": "{:.2f} MiB".format(os.path.getsize(cover) / 1024 / 1024)}

            _len = max(map(len, info.keys()))
            self.image_info = "\n".join(f"{k.ljust(_len)}: {v}" for k, v in info.items())

        self._set_geometry()

        self.update()

    def change_opacity(self) -> None:
        self.opacity = next(OPACITY_CYCLE)

        self.opacity_effect.setOpacity(self.opacity)

        if self.opacity == 1:
            # 拦截鼠标事件
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        else:
            # 鼠标事件透传
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.update()
        toast_notify(f"Cover opacity: {self.opacity}")

    #################### 重写方法 ####################

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

        # 有封面 展示详情 时
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

        # 无封面 展示详情 时
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

        # 有封面 不展示详情 时
        elif self.pix and self.opacity == 0.2:
            painter.drawPixmap(0, 0, self.scaled_pix)

        # 其余情况
        else:
            # 空白
            pass

    ######## 内部方法 ########

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

    @with_busy_cursor
    def _on_image_pasted(self) -> None:
        # 不展示详情时 跳过
        if not self.opacity == 1:
            return
        
        img = QGuiApplication.clipboard().image()
        if not img.isNull():
            ba = QByteArray()
            buffer = QBuffer(ba)
            buffer.open(QBuffer.OpenModeFlag.WriteOnly)
            img.save(buffer, "PNG")
            self.image_pasted.emit(bytes(ba))
