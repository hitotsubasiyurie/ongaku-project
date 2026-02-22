from pathlib import Path
from types import SimpleNamespace

import rtoml

from src.core.settings import settings, update_settings_comments


def _load_toml(p: Path) -> dict:
    return rtoml.load(p) if p.is_file() else {}


_data = {
    **_load_toml(Path("langs", "en.toml")),
    **_load_toml(Path("langs", f"{settings.language}.toml"))
}


MESSAGE = SimpleNamespace(**_data)

# 更新配置文件中的注释说明至对应语言版本
update_settings_comments(MESSAGE)

