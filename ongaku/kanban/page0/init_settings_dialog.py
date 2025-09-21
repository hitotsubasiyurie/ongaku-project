import os

from PySide6.QtWidgets import QDialog, QGridLayout, QPushButton, QFileDialog, QLabel

from ongaku.core.settings import global_settings


class InitSettingsDialog(QDialog):

    def setup_ui(self) -> None:
        self.setWindowTitle("Init Settings")
        self.resize(500, 150)
        layout = QGridLayout(self)

        # metadata
        self.md_dir_field = QLabel(global_settings.metadata_directory or "Select metadata directory...")
        layout.addWidget(self.md_dir_field, 0, 0)

        self.md_dir_btn = QPushButton("…")
        self.md_dir_btn.setFixedWidth(30)
        layout.addWidget(self.md_dir_btn, 0, 1)

        # resource
        self.res_dir_field = QLabel(global_settings.resource_directory or "Select resource directory...")
        layout.addWidget(self.res_dir_field, 1, 0)

        self.res_dir_btn = QPushButton("…")
        self.res_dir_btn.setFixedWidth(30)
        layout.addWidget(self.res_dir_btn, 1, 1)

        # OK 按钮
        self.ok_btn = QPushButton("OK")
        layout.addWidget(self.ok_btn, 2, 0, 1, 2)

    def setup_event(self) -> None:
        self.md_dir_btn.clicked.connect(lambda: self._choose_dir(self.md_dir_field))
        self.res_dir_btn.clicked.connect(lambda: self._choose_dir(self.res_dir_field))
        self.ok_btn.clicked.connect(self._on_ok_clicked)

    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.setup_event()

    # 内部方法
    def _choose_dir(self, label: QLabel):
        path = QFileDialog.getExistingDirectory(self, "Select directory")
        if path:
            label.setText(path)

    def _on_ok_clicked(self):
        md_dir, res_dir = self.md_dir_field.text().strip(), self.res_dir_field.text().strip()
        if not all(map(os.path.isdir, [md_dir, res_dir])):
            return

        global_settings.metadata_directory = md_dir
        global_settings.resource_directory = res_dir

        self.accept()
