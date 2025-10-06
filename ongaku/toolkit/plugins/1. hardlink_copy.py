import time
from pathlib import Path

from tqdm import tqdm

from ongaku.core.logger import lprint
from ongaku.core.settings import  global_settings
from ongaku.toolkit.toolkit_utils import easy_linput
from ongaku.toolkit.message import MESSAGE


PLUGIN_NAME = [""]


def hardlink_copy():
    lprint(MESSAGE.LRH6QG61)
    
    src_given: Path = easy_linput(MESSAGE.CGXLT9YQ, return_type=Path)
    dst_given: Path = easy_linput(MESSAGE.P8C3P4XW, return_type=Path)

    if not src_given.exists() or dst_given.exists():
        lprint(MESSAGE.O5HIF3EV)
        return

    st = time.time()

    if src_given.is_file():
        dst_given.hardlink_to(src_given)
        lprint(MESSAGE.KOQD2Y16.format(1, 0, time.time()-st))
        return

    dst_given.mkdir(parents=True, exist_ok=True)

    src_files = list(src_given.rglob("*"))
    dst_files = [dst_given / src.relative_to(src_given) for src in src_files]

    file_count, dir_count = 0, 0
    for src, dst in tqdm(zip(src_files, dst_files), total=len(src_files)):
        if src.is_dir():
            dst.mkdir()
            dir_count += 1
        else:
            dst.hardlink_to(src.resolve())
            file_count += 1

    lprint(MESSAGE.KOQD2Y16.format(file_count, dir_count, time.time()-st))
