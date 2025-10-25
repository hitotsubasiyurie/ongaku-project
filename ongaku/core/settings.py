from pathlib import Path
from typing import Any, Literal

import rtoml
import tomli_w
from pydantic import BaseModel, Field


SETTINGS_FILE = Path("./settings.toml")


class _GlobalSettings(BaseModel, validate_assignment=True):

    # 控制 自动保存
    _auto_save: bool = False

    log_level: Literal[1, 2, 3, 4] = Field(
        default=2, 
        description='Options: 1 (debug), 2 (info), 3 (warning), 4 (error)'
    )

    language: Literal["en", "zh", "ja", "ko"] = Field(
        default="en", 
        description='Interface language. Options: "en" (English), "zh" (Chinese), "ja" (Japanese), "ko" (Korean)'
    )

    temp_directory: str = Field(
        default="D:\\ongaku-tmp", 
        description=r'Directory for storing temporary files (logs, cache, etc.), e.g. "D:\\ongaku-tmp"',
        min_length=1
    )

    metadata_directory: str = Field(
        default="D:\\ongaku-metadata", 
        description=r'Directory for storing album metadata files, e.g. "D:\\ongaku-metadata"',
        min_length=1
    )

    resource_directory: str = Field(
        default="D:\\ongaku-resource", 
        description=r'Directory for storing album audio files, e.g. "D:\\ongaku-resource"',
        min_length=1
    )

    ui_color_theme: Literal["dark", "light"] = Field(
        default="dark", 
        description='Visual theme for the interface. Options: "dark", "light"'
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
        # 生成配置文件
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
        
        # 非法字段使用默认值
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


