import os
from PIL import Image

from PySide6.QtCore import Qt, QEvent, QObject
from PySide6.QtGui import QPixmap, QPalette
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget

from ongaku.core.kanban import AlbumKanBan


class CoverLabel(QLabel):

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        self.pix: QPixmap = None
        self.image_info: str = None

        # 透明效果
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(0.2)
        self.setGraphicsEffect(self.opacity_effect)

        # 鼠标事件透传
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.raise_()

        # 对齐
        self.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # 信息标签
        self.info_label = QLabel(self)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.info_label.hide()
        # info_label 字体 黑色
        palette = self.info_label.palette()
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.black)
        self.info_label.setPalette(palette)

        # info_label 字体 粗体
        font = self.info_label.font()
        font.setBold(True)
        self.info_label.setFont(font)

        # 监听父类
        parent.installEventFilter(self)

    def set_album_kanban(self, album_kanban: AlbumKanBan) -> None:
        cover = album_kanban.cover
        if not cover:
            self.clear()
            return

        with Image.open(cover) as img:
            info = {"filename": os.path.basename(cover), "format": img.format, "mode": img.mode,
                    "resolution": img.size, "file_size": "{:.2f} MiB".format(os.path.getsize(cover) /1024/1024)}

        _len = max(map(len, info.keys()))
        text = "\n".join(f"{k.ljust(_len)}: {v}" for k, v in info.items())
        self.info_label.setText(text)
        # 适应文本大小
        self.info_label.adjustSize()

        self.pix = QPixmap(cover)

        self._set_geometry()

# TODO: 改成 show
    def toggle_transparent(self, transparent: bool = None) -> None:
        if transparent is None:
            transparent = self.opacity_effect.opacity() == 1
        
        # 存在封面时，才非透明化
        if not transparent and self.pix:
            self.opacity_effect.setOpacity(1)
            self.info_label.show()
        else:
            self.opacity_effect.setOpacity(0.2)
            self.info_label.hide()

    # 重写方法

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        # 布局存在元素时才需要适应位置
        if self.pix and obj == self.parent():
            if event.type() in (QEvent.Type.Resize, QEvent.Type.Move):
                self._set_geometry()
        return super().eventFilter(obj, event)

    def clear(self) -> None:
        self.pix = None
        self.image_info = None
        self.info_label.clear()
        self.opacity_effect.setOpacity(0.2)
        return super().clear()

    # 内部方法

    def _set_geometry(self):
        parent: QWidget = self.parent()

        # 缩放适配
        scaled = self.pix.scaled(parent.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.setPixmap(scaled)
        self.resize(scaled.size())
        self.info_label.move(5, 5)

        # 坐标 是相对于父类的
        x = parent.width() - self.width()
        y = parent.height() - self.height()
        self.move(x, y)

