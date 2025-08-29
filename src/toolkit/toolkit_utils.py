from pathlib import Path
from typing import Any, Type

from src.logger import linput


def easy_linput(prompt: object  = "", default: Any = None, return_type: Type = str) -> Any:

    if default is not None and not isinstance(default, return_type):
        raise TypeError(f"Default value invalid. Expecting type {return_type.__name__}")

    while True:
        val = linput(prompt)
        if not val:
            if default is None:
                continue
            return default
        else:
            try:
                if return_type == Path:
                    val = Path(val.strip("'\""))
                else:
                    val = return_type(val)
                return val
            except Exception:
                continue



