import os
from pathlib import Path

import rtoml
from attrs import define, field, validators, fields
from cattrs import Converter

SETTINGS_FILE = Path("settings.toml")

_LOG_LEVELS = (1, 2, 3, 4, 5)
_LANGUAGES = ("en", "zh_cn", "ja", "ko")
_COLOR_THEMES = ("dark", "light")


@define(slots=True, frozen=True)
class _Settings:
    """只读配置"""

    log_level: int = field(default=2, validator=validators.in_(_LOG_LEVELS))
    language: str = field(default="zh_cn", validator=validators.in_(_LANGUAGES))

    temp_directory: str = field(default=r"D:\ongaku-tmp", converter=os.path.abspath)
    metadata_directory: str = field(default=r"D:\ongaku-metadata", converter=os.path.abspath)
    resource_directory: str = field(default=r"D:\ongaku-resource", converter=os.path.abspath)

    ui_color_theme: str = field(default="light", validator=validators.in_(_COLOR_THEMES))
    ui_font_size: int = field(default=9, validator=validators.gt(0))
    ui_font_family: str = field(default="JetBrains Mono")
    ui_cov_sources: str = field(default="amazonmusic,applemusic,itunes,ototoy,kkbox,lastfm,musicbrainz,discogs,soundcloud")
    ui_cov_country: str = field(default="jp")

    @classmethod
    def load(cls) -> "_Settings":
        if not SETTINGS_FILE.exists():
            obj = cls()
            return obj

        try:
            text = SETTINGS_FILE.read_text(encoding="utf-8")
            data = rtoml.loads(text)
        except Exception as e:
            print(f"Failed to parse settings file. {text} {e}")
            return cls()

        for attr in fields(cls):
            name = attr.name
            if name in data:
                try:
                    attr.validator and attr.validator(None, attr, data[name])
                except Exception as e:
                    print(f"Invalid field value (read): {name} {e}")
                    data.pop(name)

        converter = Converter()
        return converter.structure(data, cls)


settings = _Settings.load()

