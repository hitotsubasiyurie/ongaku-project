import os
from pathlib import Path

import rtoml
from attrs import define, field, validators, fields
from cattrs import Converter

from src.utils import dump_toml

SETTINGS_FILE = Path("settings.toml")

_LOG_LEVELS = (1, 2, 3, 4, 5)
_LANGUAGES = ("en", "zh-CN", "ja", "ko")
_COLOR_THEMES = ("dark", "light")


@define(slots=True, frozen=True)
class _Settings:
    """只读配置"""

    TMP_DIRECTORY = os.path.abspath("tmp")
    BIN_DIRECTORY = os.path.abspath("bin")

    log_level: int = field(default=2, validator=validators.in_(_LOG_LEVELS))
    language: str = field(default="en", validator=validators.in_(_LANGUAGES))

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


g_settings = _Settings.load()


def update_settings_comments(g_message) -> None:
    set2comment = {
        _Settings.log_level.__name__: g_message.SET_20260131_090300,
        _Settings.language.__name__: g_message.SET_20260131_090301,

        _Settings.metadata_directory.__name__: g_message.SET_20260131_090303,
        _Settings.resource_directory.__name__: g_message.SET_20260131_090304,

        _Settings.ui_color_theme.__name__: g_message.SET_20260131_090306,
        _Settings.ui_font_size.__name__: g_message.SET_20260131_090307,
        _Settings.ui_font_family.__name__: g_message.SET_20260131_090308,
        _Settings.ui_cov_sources.__name__: g_message.SET_20260131_090310,
        _Settings.ui_cov_country.__name__: g_message.SET_20260131_090310,
    }
    # 序列化
    lines = []

    for attr in fields(_Settings):
        name = attr.name
        comment = set2comment.get(name)
        if comment:
            lines.append("# " + comment.replace("\n", "\n# "))
        toml_str = dump_toml({name: getattr(g_settings, name)}).strip()
        lines.append(toml_str)
        lines.append("")

    text = "\n".join(lines)

    # 有差异时写入
    if not SETTINGS_FILE.is_file() or text != SETTINGS_FILE.read_text(encoding="utf-8"):
        SETTINGS_FILE.write_text(text, encoding="utf-8")
