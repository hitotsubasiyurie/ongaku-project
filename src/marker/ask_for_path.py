import sys
import json
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QFileDialog, QLabel, QMessageBox
)
from PySide6.QtGui import QIcon

SETTINGS_FILE = Path("settings.json")


def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_settings(settings: dict) -> None:
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")


class SettingsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("选择路径")
        self.resize(500, 160)

        self.settings = load_settings()
        layout = QVBoxLayout(self)

        # metadata 输入框 + 按钮
        layout.addWidget(QLabel("ongaku-metadata:"))
        self.metadata_edit = self._make_path_input(self.settings.get("metadata", ""))

        # resource 输入框 + 按钮
        layout.addWidget(QLabel("ongaku-resource:"))
        self.resource_edit = self._make_path_input(self.settings.get("resource", ""))

        # 保存按钮
        btn_save = QPushButton("保存设置")
        btn_save.clicked.connect(self.save_and_close)
        layout.addWidget(btn_save)

    def _make_path_input(self, text: str) -> QLineEdit:
        """生成一个带选择按钮的行"""
        hbox = QHBoxLayout()
        edit = QLineEdit(text)
        btn = QPushButton("…")
        btn.setFixedWidth(30)
        btn.setToolTip("选择目录")
        btn.clicked.connect(lambda: self.choose_dir(edit))
        hbox.addWidget(edit)
        hbox.addWidget(btn)
        self.layout().addLayout(hbox)
        return edit

    def choose_dir(self, line_edit: QLineEdit):
        path = QFileDialog.getExistingDirectory(self, "选择目录")
        if path:
            line_edit.setText(path)

    def save_and_close(self):
        settings = {
            "metadata": self.metadata_edit.text().strip(),
            "resource": self.resource_edit.text().strip(),
        }
        save_settings(settings)
        QMessageBox.information(self, "成功", "设置已保存到 settings.json")
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = SettingsWindow()
    w.show()
    sys.exit(app.exec())
