from pathlib import Path
from typing import Any, Literal

import rtoml
import tomli_w
from pydantic import BaseModel, Field


SETTINGS_FILE = Path("./settings.toml")


class _GlobalSettings(BaseModel, validate_assignment=True):

    language: Literal["en", "zh", "ja"] = Field(default="en", description='["en", "zh", "ja"], default is "en"')
    temp_directory: str = Field(default="./tmp", 
                                description="used to store the temporary files of the program, such as logs, etc")
    metadata_directory: str = Field(default="", description="")
    resource_directory: str = Field(default="", description="")

    ui_color_theme: Literal["dark", "light"] = Field(default="dark", description='["dark", "light"], default is "dark"')
    ui_font_size: int = Field(default=9, gt=0, description="")
    ui_font_family: str = Field(default="JetBrains Mono", description="")

    # 控制 自动保存
    _auto_save: bool = True

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
        obj._auto_save = False
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


