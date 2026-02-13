from pathlib import Path
from types import SimpleNamespace

import rtoml
from attrs import fields

from src.utils import dump_toml
from src.core.settings import SETTINGS_FILE, settings, _Settings


def _load_toml(p: Path) -> dict:
    return rtoml.load(p) if p.is_file() else {}


_data = {
    **_load_toml(Path("langs", "en.toml")),
    **_load_toml(Path("langs", f"{settings.language}.toml"))
}


MESSAGE = SimpleNamespace(**_data)


################################################################################
### 更新配置文件中的注释说明至对应语言版本
################################################################################


_SETTING2COMMENT = {
    _Settings.log_level.__name__: MESSAGE.SET_20260131_090300,
    _Settings.language.__name__: MESSAGE.SET_20260131_090301,

    _Settings.temp_directory.__name__: MESSAGE.SET_20260131_090302,
    _Settings.metadata_directory.__name__: MESSAGE.SET_20260131_090303,
    _Settings.cover_directory.__name__: MESSAGE.SET_20260131_090309,
    _Settings.resource_directory.__name__: MESSAGE.SET_20260131_090304,

    _Settings.ui_color_theme.__name__: MESSAGE.SET_20260131_090306,
    _Settings.ui_font_size.__name__: MESSAGE.SET_20260131_090307,
    _Settings.ui_font_family.__name__: MESSAGE.SET_20260131_090308,
    _Settings.ui_cov_sources.__name__: MESSAGE.SET_20260131_090310,
    _Settings.ui_cov_country.__name__: MESSAGE.SET_20260131_090310,
}


def _update_settings_comments() -> None:
    # 序列化
    lines = []

    for attr in fields(_Settings):
        name = attr.name
        comment = _SETTING2COMMENT.get(name)
        if comment:
            lines.append("# " + comment.replace("\n", "\n# "))
        toml_str = dump_toml({name: getattr(settings, name)}).strip()
        lines.append(toml_str)
        lines.append("")

    text = "\n".join(lines)

    # 有差异时写入
    if not SETTINGS_FILE.is_file() or text != SETTINGS_FILE.read_text(encoding="utf-8"):
        SETTINGS_FILE.write_text(text, encoding="utf-8")


_update_settings_comments()

