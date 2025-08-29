import os
import time
from pathlib import Path

from tqdm import tqdm

from src.toolkit.message import MESSAGE
from src.toolkit.toolkit_utils import easy_linput
from src.logger import lprint


def hardlink_copy():
    src_given: Path = easy_linput(MESSAGE.CGXLT9YQ, return_type=Path)
    dst_given: Path = easy_linput(MESSAGE.P8C3P4XW, return_type=Path)

    st = time.time()

    if src_given.is_file():
        dst_given.hardlink_to(src_given)
        lprint(MESSAGE.KOQD2Y16.format(0, 1, time.time()-st))
        return

    dst_given.mkdir(parents=True, exist_ok=True)

    src_files = list(src_given.rglob("*"))
    dst_files = [dst_given / src.relative_to(src_given) for src in src_files]

    file_count, dir_count = 0, 0
    for src, dst in tqdm(zip(src_files, dst_files)):
        if src.is_dir():
            dst.mkdir()
            dir_count += 1
        else:
            dst.hardlink_to(src.resolve())
            file_count += 1

    lprint(MESSAGE.KOQD2Y16.format(dir_count, file_count, time.time()-st))

