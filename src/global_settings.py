import sys
from pathlib import Path
from typing import Any, Literal

import orjson
from pydantic import BaseModel


SETTINGS_FILE = Path(sys.argv[0]).parent / "settings.json"


class _GlobalSettings(BaseModel, validate_assignment=True):

    language: str | None = None
    temp_directory: str | None = None
    metadata_directory: str | None = None
    resource_directory: str | None = None

    @classmethod
    def load(cls) -> "_GlobalSettings":
        if not SETTINGS_FILE.exists():
            return cls()
        try:
            data = orjson.loads(SETTINGS_FILE.read_bytes())
            return cls(**data)
        except Exception:
            return cls()
    
    def __setattr__(self, name: Any, value: Any) -> None:
        super().__setattr__(name, value)
        SETTINGS_FILE.write_bytes(
            orjson.dumps(self.model_dump(), option=orjson.OPT_INDENT_2))


global_settings = _GlobalSettings.load()


