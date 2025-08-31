import os
import sys
import time
from pathlib import Path

import orjson
from tqdm import tqdm
import numpy
from scipy.optimize import linear_sum_assignment

from src.logger import logger, lprint
from src.toolkit.message import MESSAGE
from src.toolkit.toolkit_utils import easy_linput, loop_for_actions
from src.basemodels import Album, _validate_strtuple
from src.basemodel_utils import count_album_similarity, album_to_unique_str
from src.toolkit.metadata_source.musicbrainz_database import MusicBrainzDatabase
from src.repository.ongaku_repository import dump_albums_to_toml, load_albums_from_toml


SEPERATE = f"{'-'*16} seperate {'-'*16}"

NO_APPLY = "[_NO_APPLY_]"
YES_APPLY = "[_YES_APPLY_]"
SIMILARITY = "SIMILARITY: "

DST_ALBUM = "DST_ALBUM: "
SRC_ALBUM = "SRC_ALBUM: "

dst_file: Path = None
src_file: Path = None


def generate_merge_log() -> None:
    merge_log = dst_file.parent / "merge.log"
    content = ""

    skip_keyword: str = easy_linput(MESSAGE.Q9YNQ293, default="", return_type=str)
    min_sim: float = easy_linput(MESSAGE.R3VY3KF6, default=90.0, return_type=float)
    enable_catno_filter: bool = easy_linput(MESSAGE.BHX8PWTM, default="Y", return_type=str)  == "Y"

    # 跳过 已存在 link keyword 的 目标专辑
    dst_albums = [a for a in load_albums_from_toml(dst_file) 
                  if not skip_keyword or all(skip_keyword not in l for l in a.links)]
    src_albums = load_albums_from_toml(src_file)

    sim_matrix = numpy.zeros((len(dst_albums), len(src_albums)), dtype=numpy.float32)
    for i, da in enumerate(tqdm(dst_albums, desc="Count albums similarity", miniters=0)):

        # 提前拦截 catalognumber 相等的结果
        if enable_catno_filter:
            matches = [(j, sa) for j, sa in enumerate(src_albums) if da.catalognumber == sa.catalognumber]
            if matches:
                for j, sa in matches:
                    sim_matrix[i, j] = count_album_similarity(da, sa)
                continue

        for j, sa in enumerate(src_albums):
            sim_matrix[i, j] = count_album_similarity(da, sa)

    lprint(MESSAGE.V7VQSYWB)
    row_ind, col_ind = linear_sum_assignment(sim_matrix, maximize=True)

    for row, col in zip(row_ind, col_ind):

        if sim_matrix[row][col] < min_sim:
            continue

        lines = []
        lines.append("")
        lines.append(NO_APPLY)
        lines.append(SIMILARITY + format(sim_matrix[row][col], '.2f'))
        lines.append("")
        lines.append(DST_ALBUM + album_to_unique_str(dst_albums[row]))
        lines.append(SRC_ALBUM + album_to_unique_str(src_albums[col]))
        content += "\n" + SEPERATE + "\n".join(lines) + "\n"

    merge_log.write_text(content, encoding="utf-8")

    lprint(MESSAGE.NEJU5R13.format(merge_log))


def apply_merge_log() -> None:

    merge_log: Path = easy_linput(MESSAGE.DERFEKFV, return_type=Path)
    apply_mask: str = easy_linput(MESSAGE.J1H47YFK)
    apply_when_no_value: bool = easy_linput(MESSAGE.PLCIYBZW, default="Y", return_type=str)  == "Y"

    dst_albums, src_albums = load_albums_from_toml(dst_file), load_albums_from_toml(src_file)
    dst_unique_str_to_albums = {album_to_unique_str(a): a for a in dst_albums}
    src_unique_str_to_albums = {album_to_unique_str(a): a for a in src_albums}

    for line in merge_log.read_text(encoding="utf-8").split("\n"):
        if line.startswith(SEPERATE):
            apply, dst, src = [None] * 3
        elif line.startswith(YES_APPLY):
            apply = True
        elif line.startswith(DST_ALBUM):
            dst = dst_unique_str_to_albums[line.removeprefix(DST_ALBUM)]
        elif line.startswith(SRC_ALBUM):
            src = src_unique_str_to_albums[line.removeprefix(SRC_ALBUM)]
            if not apply:
                continue
            # 开始应用
            for b, field in zip(apply_mask, ["catalognumber", "date", "album", "tracks"]):
                if (int(b) and getattr(src, field)) or (apply_when_no_value and not getattr(dst, field)):
                    setattr(dst, field, getattr(src, field))

            # 添加 links
            dst.links = _validate_strtuple(dst.links + src.links)

            # 源头 专辑 去除
            src_albums.remove(src)

    dump_albums_to_toml(dst_albums, dst_file)
    dump_albums_to_toml(src_albums, src_file)

    lprint(MESSAGE.JNAIXTGI)


def merge_metadata_files():
    lprint(MESSAGE.BGF1DM8D)

    global dst_file, src_file
    dst_file = easy_linput(MESSAGE.BB8Z9OR4, return_type=Path)
    src_file = easy_linput(MESSAGE.O7USULLZ, return_type=Path)

    message2action = {
        MESSAGE.VOLF5PUD: generate_merge_log,
        MESSAGE.GCXAW6BC: apply_merge_log,
        MESSAGE.CLZWFPBZ: None
    }

    loop_for_actions(message2action)

