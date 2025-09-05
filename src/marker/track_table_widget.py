
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QTableWidgetItem, QSlider, QPushButton, QLabel, QHeaderView, QStyleFactory, QGridLayout, 
    QFrame, )
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from src.basemodels import Album, Track
from src.kanban.kanban import ResourceState


class TrackTableWidget(QTableWidget):

    def setup_context_menu(self) -> None:
        # 初始化 右键菜单
        pass

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        # 表格无边框
        self.setShowGrid(False)
        self.setFrameShape(QFrame.Shape.NoFrame)
        # 可编辑
        self.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
        # 多选
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        # 可排序
        self.setSortingEnabled(True)
        # 像素滚动
        self.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)

        # 隐藏 行 标题
        self.verticalHeader().setVisible(False)

        # 字体大小
        font_size = self.font().pixelSize()

        # 设置 列 标题
        self.setColumnCount(6)
        # TODO: size 用绿色黄色字体标明有损无损
        self.setHorizontalHeaderLabels(["Size", "Title", "Artist", "Album", "Date", "Mark"])

        header = self.horizontalHeader()
        column_size = [font_size*5, 0, font_size*16, font_size*16, font_size*6, font_size*3]
        for i, w in enumerate(column_size):
            if w:
                self.setColumnWidth(i, w)
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
            else:
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

    ## TODO: 当前的数据结构，并不符合 track table 。怎么排序，怎么修改
    ## USERROLE
    ## 

    def set_albums(self, albums: list[Album], track_states: list[list[ResourceState]]) -> None:
        ## 大小？
        for album, t_states in zip(albums, track_states):























