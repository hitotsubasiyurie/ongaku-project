from pathlib import Path
from typing import Any, Type, Callable, TypeVar
from types import SimpleNamespace

from ongaku.core.logger import linput, lprint, logger
from ongaku.core.settings import  global_settings


MESSAGE = SimpleNamespace()


if global_settings.language == "zh":
    MESSAGE.OG9 = "请选择动作："
    MESSAGE.K98 = "退出"
elif global_settings.language == "ja":
    pass
else:
    pass

T = TypeVar("T")


def easy_linput(prompt: object  = "", default: Any = None, return_type: Type[T] = str) -> T:
    """
    :param default: 默认为 None 时，会循环提示输入。
    """

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
        lprint("\n".join(f"{i+1}. {m}" for i, m in enumerate(messages)) + "\n")
        number = easy_linput(MESSAGE.OG9, return_type=int)
        lprint()

        if not (0 <= number - 1 <= len(messages)):
            continue

        try:
            lprint(f"{'-'*8} {messages[number - 1]} {'-'*8}")
            func = actions[number - 1]
            if not func:
                return
            func()
            lprint("-"*32)
        except Exception as e:
            lprint(f"Error: {e}")
            logger.error("", exc_info=1)
