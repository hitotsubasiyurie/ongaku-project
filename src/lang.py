from pathlib import Path
from types import SimpleNamespace

import rtoml

from src.core.settings import global_settings


def _load(p: Path) -> dict:
    return rtoml.load(p) if p.is_file() else {}


_data = {
    **_load(Path("lang", "en.toml")),
    **_load(Path("lang", f"{global_settings.language}.toml"))
}


MESSAGE = SimpleNamespace(**_data)
