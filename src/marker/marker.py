from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QSlider, QPushButton, QLabel, QHeaderView, QStyleFactory, QGridLayout, )
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from src.kanban.kanban import ThemeKanBan


class MarkerMainWindow(QWidget):

    def setup_ui(self) -> None:
        self.setWindowTitle("Marker")

        # 初始化 UI
        grid_layout = QGridLayout()
        self.setLayout(grid_layout)

        # 播放器
        self.player = QMediaPlayer(self)
        self.output = QAudioOutput(self)
        self.player.setAudioOutput(self.output)
        self.player.setLoops(-1)

        # 歌曲列表
        self.table = QTableWidget()

        # 控件
        self.slider = QSlider(Qt.Horizontal)
        self.time_label = QLabel()
        self.ctrl_btn = QPushButton("CTRL")
        self.next_btn = QPushButton("NEXT")


    def setup_event(self) -> None:
        # 初始化 事件
        pass

    def __init__(self, kanban: ThemeKanBan) -> None:
        super().__init__()

        self.current_theme_kanban: ThemeKanBan = kanban
        self.current_theme_kanban.theme_name
        ThemeKanBan().tracks_files

        self.setup_ui()
        self.setup_event()





