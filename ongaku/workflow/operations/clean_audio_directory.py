import shutil
import itertools
from pathlib import Path

from ongaku.core.settings import global_settings
from ongaku.core.constants import AUDIO_EXTS
from ongaku.core.logger import lprint
from ongaku.workflow.common import easy_linput


if global_settings.language == "zh":
    OPERATION_NAME = "清理音频目录"
    class MESSAGE:
        OG9f67 = "请输入音频资源父目录："
        DR7BB5 = "清理音频目录完成。"
elif global_settings.language == "ja":
    pass
else:
    pass


def main() -> None:
    parent_dir = easy_linput(MESSAGE.OG9f67, return_type=Path)

    # 从下往上 删除 没有子孙音频文件的 目录
    for d in reversed(list(filter(Path.is_dir, parent_dir.rglob("*")))):
        if not list(itertools.chain.from_iterable(d.rglob(f"*{ext}") for ext in AUDIO_EXTS)):
            shutil.rmtree(d)

    lprint(MESSAGE.DR7BB5)

