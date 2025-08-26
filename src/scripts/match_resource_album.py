import sys
import json
import os
import re
import shutil
import itertools
from difflib import SequenceMatcher
from typing import Generator
from pathlib import Path
import tomllib
from functools import cache

import numpy
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.logger import logger
from src.common.constants import METADATA_PATH, TMP_PATH
from src.metadata_source.musicbrainz_api import MusicBrainzAPI
from src.metadata_source.musicbrainz_database import MusicBrainzDatabase
from src.common.basemodels import Album, Track
from src.utils import read_audio_tags
from src.ongaku_library.ongaku_library import (dump_album_json, album_filename, OngakuScanner, 
    load_album_json, AUDIO_EXTS, track_filenames)


SEPERATE = f"\n{'-'*16} seperate {'-'*16}\n"

ALBUM_SIMILARITY = "ALBUM_SIMILARITY: "
TRACK_SIMILARITY = "TRACK_SIMILARITY: "

RESOURCE_DIRECTORY_ = "RESOURCE_DIRECTORY_: "
DESTINATE_DIRECTORY = "DESTINATE_DIRECTORY: "
RESOURCE_ALBUM = "RESOURCE_ALBUM: "
MATCHING_ALBUM = "MATCHING_ALBUM: "

RESOURCE_AUDIOFILE_ = "RESOURCE_AUDIOFILE_: "
DESTINATE_AUDIOFILE = "DESTINATE_AUDIOFILE: "
RESOURCE_TRACK = "RESOURCE_TRACK: "
MATCHING_TRACK = "MATCHING_TRACK: "






def apply_matching_log(matching_log: Path, resource_save_dir: Path) -> None:
    for line in matching_log.open("r", encoding="utf-8"):
        if line.startswith(RESOURCE_DIRECTORY_):
            src_dir = line.removeprefix(RESOURCE_DIRECTORY_)
        elif line.startswith(DESTINATE_DIRECTORY):
            dst_dir = line.removeprefix(DESTINATE_DIRECTORY)
        elif line.startswith(RESOURCE_AUDIOFILE_):
            src_file = line.removeprefix(RESOURCE_AUDIOFILE_)
        elif line.startswith(DESTINATE_AUDIOFILE):
            dst_file = line.removeprefix(DESTINATE_AUDIOFILE)
            Path(src_dir, src_file).rename(dst_dir, dst_file)


def clean_resource_parent(resource_parent: Path) -> None:
    for d in reversed(list(filter(Path.is_dir, resource_parent.rglob("*")))):
        if not list(itertools.chain.from_iterable(d.rglob(f"*{ext}") for ext in AUDIO_EXTS)):
            shutil.rmtree(d)


if __name__ == "__main__":

    # input 输入
    theme_file = input(f"Please input theme metadata file: ").strip("'\"")
    resource_parent = input(f"Please input resource parent directory: ").strip("'\"")
    resource_save_dir = input(f"Please input resource save directory: ").strip("'\"")
    tmp_dir = input(f"Please input temp directory ({TMP_PATH}): ").strip("'\"") or TMP_PATH

    if not theme_file or not resource_parent or not resource_save_dir or not tmp_dir:
        sys.exit(0)

    theme_file, resource_parent, resource_save_dir, tmp_dir = Path(theme_file), Path(resource_parent), Path(resource_save_dir), Path(tmp_dir)

    matching_log = tmp_dir / "resource_matching.log"
    # analyze_save_file = tmp_dir / "analyze.json"

    theme_albums = list(map(Album.from_dict, tomllib.loads(theme_file.read_text(encoding="utf-8")).values()))

    # 循环交互

    while True:

        os.system("cls")
        print("Please input action number：")
        print("1. Generate matching log")
        print("2. Apply matching log")
        print("3. Clean resource parent directory")
        action = int(input(""))

        if action == 1:
            show_detail = input(f"show detail? (Y/N) (default N) ") == "Y"
            generate_match_log(resource_parent, resource_save_dir, matching_log, show_detail)

        elif action == 2:
            apply_matching_log()

        elif action == 3:
            clean_resource_parent(resource_parent)

# 扫描，构建物理资源专辑模型
# 元数据文件 与 物理对应专辑模型 一一配对
# 移动物理资源文件
# 删除没有音频的文件夹，从下往上删除


