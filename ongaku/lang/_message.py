from pathlib import Path
from types import SimpleNamespace

import rtoml

from ongaku.core.settings import global_settings


_msg_file = Path("ongaku", "lang", f"{global_settings.language}.toml")
MESSAGE = SimpleNamespace(**rtoml.loads(_msg_file.read_text(encoding="utf-8")))



