from pathlib import Path
from typing import Any, Type, Callable

from src.logger import linput, lprint, logger
from src.toolkit.message import MESSAGE


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


def loop_for_actions(message2action: dict[str, Callable]) -> None:
    messages, actions = list(message2action.keys()), list(message2action.values())
    while True:
        lprint("\n".join(f"{i+1}. {m}" for i, m in enumerate(messages)))
        number = easy_linput(MESSAGE.AW9FDB6V, return_type=int)

        if not (0 <= number - 1 <= len(messages)):
            continue

        try:
            lprint(f"{'-'*8} {messages[number - 1]} {'-'*8}")
            func = actions[number - 1]
            if not func:
                return
            func()
            lprint("-"*32)
        except Exception:
            logger.error("", exc_info=1)
