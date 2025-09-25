import os
from PIL import Image

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QResizeEvent, QPalette
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget

from ongaku.kanban.kanban import AlbumKanBan


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
        self._resize_label()

    def toggle_transparent(self, transparent: bool = None) -> None:
        if transparent is None:
            transparent = self.opacity_effect.opacity() == 1
        
        if not transparent:
            self.opacity_effect.setOpacity(1)
            self.info_label.show()
        else:
            self.opacity_effect.setOpacity(0.2)
            self.info_label.hide()

    # 重写方法

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._resize_label()

    def clear(self) -> None:
        self.info_label.clear()
        return super().clear()

    # 内部方法

    def _resize_label(self) -> None:
        if not self.pix:
            return
        
        # 缩放适配
        scaled = self.pix.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.setPixmap(scaled)

        self.info_label.move(self.width() - scaled.width(), 0)


