from pathlib import Path
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QSlider, QPushButton, QLabel,
    QHeaderView, QStyleFactory
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput


Xname = "电波"
inDirpath = Path(r"D:\移动云盘同步盘\ongaku-resource")


class Main(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(Xname)
        self.setStyleSheet("font-size:13px;")
        
        # 播放器
        self.player = QMediaPlayer(self)
        self.output = QAudioOutput(self)
        self.player.setAudioOutput(self.output)
        self.player.setLoops(-1)

        # 歌曲列表
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["大小", "格式", "标题", "艺术家", "专辑"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.cellDoubleClicked.connect(self.on_table_double_clicked)

        # 控件
        self.slider = QSlider(Qt.Horizontal)
        self.time_label = QLabel()
        self.ctrl_btn = QPushButton("CTRL")
        self.next_btn = QPushButton("NEXT")

        # 布局
        vbox = QVBoxLayout(self)
        vbox.addWidget(self.table)

        hbox = QHBoxLayout()
        hbox.addWidget(self.slider, 4)
        hbox.addWidget(self.time_label, 1)
        hbox.addWidget(self.ctrl_btn)
        hbox.addWidget(self.next_btn)
        vbox.addLayout(hbox)

        # 信号
        self.player.positionChanged.connect(self.on_position_changed)
        self.slider.valueChanged.connect(self.on_slider_changed)
        self.ctrl_btn.clicked.connect(self.on_ctrl_clicked)
        self.next_btn.clicked.connect(lambda: self.change_current(self.current + 1))

        # 键盘快捷键
        QShortcut(QKeySequence("Space"), self, self.toggle_play_pause)
        QShortcut(QKeySequence("Left"), self, lambda: self.seek(-3000))
        QShortcut(QKeySequence("Right"), self, lambda: self.seek(3000))
        QShortcut(QKeySequence("Backspace"), self, lambda: self.player.setPosition(0))
        QShortcut(QKeySequence("Ctrl+Up"), self, lambda: self.output.setVolume(min(1.0, self.output.volume() + 0.1)))
        QShortcut(QKeySequence("Ctrl+Down"), self, lambda: self.output.setVolume(max(0.0, self.output.volume() - 0.1)))

        # 加载歌曲
        self.songpaths = sorted(
            [p for p in inDirpath.rglob("*") if p.suffix.lower() in (".mp3", ".flac", ".wav")],
            key=lambda x: x.name.upper()
        )
        self.load_table()
        self.current = 0
        if self.songpaths:
            self.change_current(0)

    def load_table(self):
        self.table.setRowCount(len(self.songpaths))
        for row, song in enumerate(self.songpaths):
            size_mb = f"{song.stat().st_size / 1024 / 1024:.2f} MB"
            self.table.setItem(row, 0, QTableWidgetItem(size_mb))
            self.table.setItem(row, 1, QTableWidgetItem(song.suffix))
            self.table.setItem(row, 2, QTableWidgetItem(song.stem))  # 简单用文件名代替标题
            self.table.setItem(row, 3, QTableWidgetItem("未知艺术家"))
            self.table.setItem(row, 4, QTableWidgetItem("未知专辑"))

    def change_current(self, index: int):
        if not (0 <= index < len(self.songpaths)):
            return
        if hasattr(self, "current"):
            self.lowlight_row(self.current)
        self.current = index
        self.highlight_row(index)
        self.play_current()

    def play_current(self):
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(str(self.songpaths[self.current])))
        self.player.play()

    def toggle_play_pause(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def seek(self, ms: int):
        self.player.setPosition(max(0, self.player.position() + ms))

    def highlight_row(self, row: int):
        for i in range(5):
            self.table.item(row, i).setBackground(QColor(21, 67, 96))
        self.table.scrollToItem(self.table.item(row, 0))

    def lowlight_row(self, row: int):
        for i in range(5):
            self.table.item(row, i).setForeground(QColor(98, 101, 103))
            self.table.item(row, i).setBackground(QColor())

    def on_position_changed(self, pos: int):
        if self.player.duration() > 0:
            self.slider.blockSignals(True)
            self.slider.setValue(100 * pos // self.player.duration())
            self.slider.blockSignals(False)
            cur_sec = pos // 1000
            dur_sec = self.player.duration() // 1000
            self.time_label.setText(f"{self.current+1}/{len(self.songpaths)}  {cur_sec}/{dur_sec}s")

    def on_slider_changed(self, value: int):
        if self.player.duration() > 0:
            self.player.setPosition(self.player.duration() * value // 100)

    def on_table_double_clicked(self, row: int, col: int):
        if col == 0:
            self.change_current(row)
        elif col == 1:
            import os
            os.startfile(self.songpaths[row].parent)

    def on_ctrl_clicked(self):
        if self.ctrl_btn.text() == "CTRL":
            self.ctrl_btn.setText("ALT")
        elif self.ctrl_btn.text() == "ALT":
            self.ctrl_btn.setText("*")
        else:
            self.ctrl_btn.setText("CTRL")


if __name__ == "__main__":
    app = QApplication([])
    app.setStyle(QStyleFactory.create("Fusion"))
    main = Main()
    main.showMaximized()
    app.exec()
