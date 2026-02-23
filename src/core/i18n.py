from pathlib import Path
from types import SimpleNamespace

import rtoml

from src.core.settings import g_settings, update_settings_comments


def _load_toml(p: Path) -> dict:
    return rtoml.load(p) if p.is_file() else {}


_data = {
    **_load_toml(Path("langs", "en.toml")),
    **_load_toml(Path("langs", f"{g_settings.language}.toml"))
}


g_message = SimpleNamespace(**_data)

# 更新配置文件中的注释说明至对应语言版本
update_settings_comments(g_message)

