from pathlib import Path
from typing import Any

import orjson
from pydantic import BaseModel


SETTINGS_FILE = Path("./settings.json")


class _GlobalSettings(BaseModel, validate_assignment=True):

    language: str = ""
    temp_directory: str = ""
    metadata_directory: str = ""
    resource_directory: str = ""
    # 可选配置
    color_theme: str = "dark"
    ui_font_size: int = 10
    ui_font_family: str = "JetBrains Mono"

    @classmethod
    def load(cls) -> "_GlobalSettings":
        if not SETTINGS_FILE.exists():
            return cls()
        try:
            data = orjson.loads(SETTINGS_FILE.read_bytes())
            return cls(**data)
        except Exception:
            return cls()
    
    def __setattr__(self, name: Any, value: Any) -> None:
        super().__setattr__(name, value)
        SETTINGS_FILE.write_bytes(
            orjson.dumps(self.model_dump(), option=orjson.OPT_INDENT_2))


global_settings = _GlobalSettings.load()


