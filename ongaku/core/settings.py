from pathlib import Path
from typing import Any, Literal, ClassVar

import rtoml
import tomli_w
from pydantic import BaseModel, Field


SETTINGS_FILE = Path("./settings.toml")


class _GlobalSettings(BaseModel, validate_assignment=True):

    # 支持的语言
    SUPPORTED_LANGS: ClassVar[list[str]] = ["en", "zh", "ja"]
    # 控制 自动保存
    _auto_save: bool = False

    log_level: Literal["en", "zh", "ja"] = Field(
        default="en", 
        description='Interface language. Options: "en" (English), "zh" (Chinese), "ja" (Japanese)'
    )

    language: Literal["en", "zh", "ja"] = Field(
        default="en", 
        description='Interface language. Options: "en" (English), "zh" (Chinese), "ja" (Japanese)'
    )

    temp_directory: str = Field(
        default="./ongaku-temp", 
        description="Directory for storing temporary files (logs, cache, etc.)",
        min_length=1
    )

    metadata_directory: str = Field(
        default="./ongaku-metadata", 
        description="Directory for storing album metadata files",
        min_length=1
    )

    resource_directory: str = Field(
        default="./ongaku-resource", 
        description="Directory for storing album audio files",
        min_length=1
    )

    ui_color_theme: Literal["dark", "light"] = Field(
        default="dark", 
        description='Visual theme for the interface. Options: "dark" or "light"'
    )

    ui_font_size: int = Field(
        default=9, 
        gt=0, 
        description="Base font size for the user interface (in points)"
    )

    ui_font_family: str = Field(
        default="JetBrains Mono", 
        description='Font family used throughout the interface. Recommended: "JetBrains Mono"',
        min_length=1
    )

    @classmethod
    def load(cls) -> "_GlobalSettings":
        if not SETTINGS_FILE.exists():
            obj = cls()
            obj.save()
            return obj

        try:
            text = SETTINGS_FILE.read_text(encoding="utf-8")
            data = rtoml.loads(text)
        except Exception as e:
            print(f"Failed to parse settings file. {text} {e}")
            return cls()
        
        # 逐个字段校验
        obj = cls()
        for name, _ in _GlobalSettings.model_fields.items():
            if name not in data:
                continue
            try:
                setattr(obj, name, data[name])
            except Exception as e:
                print(f"Invalid filed value. {name} {data[name]} {e}")
        
        obj._auto_save = True
        return obj

    def save(self):
        lines = []

        for name, field in _GlobalSettings.model_fields.items():
            desc = field.description or ""
            if desc:
                lines.append(f"# {desc}")
            toml_str = tomli_w.dumps({name: getattr(self, name)}).strip()
            lines.append(toml_str)
            lines.append("")

        SETTINGS_FILE.write_text("\n".join(lines), encoding="utf-8")

    def __setattr__(self, name: Any, value: Any) -> None:
        if value == getattr(self, name, None):
            return
        super().__setattr__(name, value)
        self._auto_save and self.save()


global_settings = _GlobalSettings.load()


