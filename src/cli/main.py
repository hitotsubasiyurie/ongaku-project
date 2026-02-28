import os
import sys
from pathlib import Path
from typing import Callable

executable = Path(sys.argv[0])

# 若是源码运行 添加导包路径
if executable.suffix == ".py":
    sys.path[0] = str(executable.parent.parent.parent)
    os.chdir(executable.parent.parent.parent)
else:
    os.chdir(executable.parent)

from src.core.settings import g_settings
from src.operations.common import loop_for_actions
from src.operations import OPERATIONS
from src.core.console import easy_cinput, cprint
from src.core.logger import logger


def loop_for_actions(message2action: dict[str, Callable]) -> None:
    messages, actions = list(message2action.keys()), list(message2action.values())
    while True:
        cprint("\n".join(f"{i+1}. {m}" for i, m in enumerate(messages)) + "\n")
        number = easy_cinput("?: ", return_type=int)
        cprint()

        if not (0 <= number - 1 <= len(messages)):
            continue

        try:
            cprint(f"{'-'*8} {messages[number - 1]} {'-'*8}")
            func = actions[number - 1]
            if not func:
                return
            func()
            cprint("-"*32)
        except Exception as e:
            cprint(f"Error: {e}")
            logger.error("", exc_info=1)


if __name__ == "__main__":

    # 初始化 目录
    for p in [g_settings.metadata_directory, g_settings.resource_directory]:
        os.makedirs(p, exist_ok=True)

    loop_for_actions(OPERATIONS)
