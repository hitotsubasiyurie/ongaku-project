from PySide6.QtWidgets import (QWidget, QSlider, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, 
    QStyle, )
from PySide6.QtGui import QMouseEvent
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import Qt, QTime, QUrl, Signal


class ClickableSlider(QSlider):

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            value = QStyle.sliderValueFromPosition(self.minimum(), self.maximum(), 
                                                   event.position().x(), self.width())
            self.setValue(value)
            self.sliderMoved.emit(value)
        super().mousePressEvent(event)


class MusicPlayerBar(QWidget):

    playback_finished = Signal()

    def setup_ui(self) -> None:
        # 初始化 UI
        # 字体高度
        fh = self.fontMetrics().height()

        self.slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.slider.setFixedHeight(fh)

        self.time_label = QLabel("00:00/00:00")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setFixedSize(fh * 6, fh * 1.5)

        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setFixedSize(fh * 2, fh * 1.5)
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(fh * 2, fh * 1.5)
        self.next_btn = QPushButton("⏭")
        self.next_btn.setFixedSize(fh * 2, fh * 1.5)

        layout = QVBoxLayout()
        layout.setSpacing(1)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        layout.addWidget(self.slider)

        h_layout = QHBoxLayout()
        h_layout.setSpacing(1)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.addWidget(self.time_label)
        h_layout.addWidget(self.prev_btn)
        h_layout.addWidget(self.play_btn)
        h_layout.addWidget(self.next_btn)

        # 居中
        h_layout.insertStretch(0)
        h_layout.insertStretch(-1)
        layout.addLayout(h_layout)

        layout.insertStretch(0)
        layout.insertStretch(-1)

    def setup_event(self) -> None:
        self.slider.sliderMoved.connect(lambda pos: self.player.setPosition(pos))
        self.play_btn.clicked.connect(self.toggle_play)
        self.player.durationChanged.connect(lambda d: self.slider.setRange(0, d))
        self.player.positionChanged.connect(self._on_player_position_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent)

        # 播放器
        self.player = QMediaPlayer(self)
        self.output = QAudioOutput(self)
        self.player.setAudioOutput(self.output)
        self.player.setLoops(QMediaPlayer.Loops.Once)

        self.setup_ui()
        self.setup_event()

    def set_media(self, file: str) -> None:
        self.time_label.clear()
        url = QUrl.fromLocalFile(file)
        self.player.setSource(url)
        self.toggle_play()

    def toggle_play(self) -> None:
        if self.player.isPlaying():
            self.player.pause()
            self.play_btn.setText("▶")
        else:
            self.player.play()
            self.play_btn.setText("⏸")

    # 内部方法

    def _on_player_position_changed(self, position: int) -> None:
        if not self.slider.isSliderDown():
            self.slider.setValue(position)

        cur_time = QTime(0, 0, 0).addMSecs(position)
        total_time = QTime(0, 0, 0).addMSecs(self.player.duration())
        self.time_label.setText(f"{cur_time.toString('mm:ss')}/{total_time.toString('mm:ss')}")

    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.play_btn.setText("▶")
            self.playback_finished.emit() 
