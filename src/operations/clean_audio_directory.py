import itertools
import shutil
from pathlib import Path

from src.core.i18n import g_message
from src.core.console import cinput, cprint, easy_linput
from src.core.storage import AUDIO_EXTS

OPERATION_NAME = g_message.WF_20251204_194010


def main() -> None:
    parent_dir = easy_linput(g_message.WF_20251204_194011, return_type=Path)

    # 从下往上 删除 没有子孙音频文件的 目录
    for d in reversed(list(filter(Path.is_dir, parent_dir.rglob("*")))):
        if not list(itertools.chain.from_iterable(d.rglob(f"*{ext}") for ext in AUDIO_EXTS)):
            shutil.rmtree(d)

    cprint(g_message.WF_20251204_194012)

