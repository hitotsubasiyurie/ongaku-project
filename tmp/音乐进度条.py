import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QSlider, QLabel,
    QPushButton, QHBoxLayout, QVBoxLayout
)
from PySide6.QtCore import Qt, QTimer


class MusicProgressBar(QWidget):
    def __init__(self, total_duration=240, parent=None):
        super().__init__(parent)

        self.total_duration = total_duration  # 总时长（秒）
        self.current_time = 0                 # 当前播放进度（秒）

        # --- 主体 slider ---
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, self.total_duration)
        self.slider.setValue(0)

        # --- 时间标签 ---
        self.time_label = QLabel(self._format_time())
        self.time_label.setAlignment(Qt.AlignCenter)

        # --- 控制按钮 ---
        self.prev_btn = QPushButton("⏮")
        self.play_btn = QPushButton("⏸")  # 初始为暂停按钮
        self.next_btn = QPushButton("⏭")

        # --- 布局 ---
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.slider)

        control_layout = QHBoxLayout()
        control_layout.addWidget(self.prev_btn)
        control_layout.addWidget(self.play_btn)
        control_layout.addWidget(self.next_btn)
        main_layout.addLayout(control_layout)

        main_layout.addWidget(self.time_label)

        # --- 信号槽 ---
        self.slider.sliderMoved.connect(self._on_slider_moved)
        self.play_btn.clicked.connect(self._toggle_play)

        # --- 模拟播放计时器 ---
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_progress)
        self.timer.start(1000)  # 每秒更新

        self.is_playing = True

    def _format_time(self) -> str:
        """格式化成 mm:ss / mm:ss"""
        cur_min, cur_sec = divmod(self.current_time, 60)
        tot_min, tot_sec = divmod(self.total_duration, 60)
        return f"{cur_min:02}:{cur_sec:02} / {tot_min:02}:{tot_sec:02}"

    def _update_progress(self):
        """播放进度更新"""
        if self.is_playing and self.current_time < self.total_duration:
            self.current_time += 1
            self.slider.setValue(self.current_time)
            self.time_label.setText(self._format_time())

    def _on_slider_moved(self, value):
        """拖动进度条"""
        self.current_time = value
        self.time_label.setText(self._format_time())

    def _toggle_play(self):
        """播放/暂停切换"""
        self.is_playing = not self.is_playing
        self.play_btn.setText("▶" if not self.is_playing else "⏸")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MusicProgressBar(total_duration=300)  # 5分钟
    w.resize(400, 120)
    w.show()
    sys.exit(app.exec())
