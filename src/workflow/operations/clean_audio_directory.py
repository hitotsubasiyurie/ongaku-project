import itertools
import shutil
from pathlib import Path

from src.core.constants import AUDIO_EXTS
from src.core.logger import lprint
from src.lang import MESSAGE
from src.workflow.common import easy_linput

OPERATION_NAME = MESSAGE.WF_20251204_194010


def main() -> None:
    parent_dir = easy_linput(MESSAGE.WF_20251204_194011, return_type=Path)

    # 从下往上 删除 没有子孙音频文件的 目录
    for d in reversed(list(filter(Path.is_dir, parent_dir.rglob("*")))):
        if not list(itertools.chain.from_iterable(d.rglob(f"*{ext}") for ext in AUDIO_EXTS)):
            shutil.rmtree(d)

    lprint(MESSAGE.WF_20251204_194012)

