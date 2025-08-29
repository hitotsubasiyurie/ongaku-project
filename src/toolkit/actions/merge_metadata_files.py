import os
import sys
import time
from pathlib import Path

import orjson
from tqdm import tqdm
from munkres import Munkres

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.logger import logger, lprint
from src.toolkit.message import MESSAGE
from src.toolkit.toolkit_utils import easy_linput
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


def generate_merge_log(dst_file: Path, src_file: Path) -> None:
    merge_log = dst_file.parent / "merge.log"
    content = ""

    skip_keyword = input("Please input link keyword to skip merge to (such as 'musicbrainz') (default None): ").strip() or None
    min_sim = float(input("Please input similarity threshold (recommend 90 -> 80 -> 75) (default 90): ").strip() or 90)
    enable_catno_filter = (input("Please input if filter catalognumber (Y/N) (default Y): ").strip() or "Y") == "Y"

    # 跳过 已存在 link keyword 的 目标专辑
    dst_albums = [a for a in load_albums_from_toml(dst_file) 
                  if not skip_keyword or all(skip_keyword not in l for l in a.links)]
    src_albums = load_albums_from_toml(src_file)

    sim_matrix = [[0] * len(src_albums) for _ in range(len(dst_albums))]
    for i, da in enumerate(tqdm(dst_albums, desc="Count albums similarity", miniters=0)):

        # 提前拦截 catalognumber 相等的结果
        if enable_catno_filter:
            matches = [(j, sa) for j, sa in enumerate(src_albums) if da.catalognumber == sa.catalognumber]
            if matches:
                for j, sa in matches:
                    sim_matrix[i, j] = -count_album_similarity(da, sa)
                continue

        for j, sa in enumerate(src_albums):
            sim_matrix[i, j] = -count_album_similarity(da, sa)

    print("Matching the most similar album...")
    indexes = Munkres().compute(sim_matrix)

    for row, col in indexes:

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

    print(f"Generated merge log successfully. {merge_log}")


def apply_merge_log(dst_file: Path, src_file: Path) -> None:

    merge_log = input(f"Please input merge log: ").strip("'\"")
    apply_mask = input("Please input metadata apply mask [catalognumber, date, album, tracks] (such as 0001): ").strip()
    apply_when_no_value = (input("Please input if apply when dst value is None (Y/N) (default Y): ").strip() or "Y") == "Y"

    if not all([merge_log, apply_mask]):
        return
    
    merge_log = Path(merge_log)

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


def merge_metadata_files():

    # input 输入

    dst_file = input(f"Please input dst metadata file (merge to): ").strip("'\"")
    src_file = input(f"Please input src metadata file (merge from): ").strip("'\"")

    if not all([dst_file, src_file]):
        sys.exit(0)

    src_file, dst_file = Path(src_file), Path(dst_file)

    # 循环交互
    while True:

        print("Please input action number:")
        print("1. Generate merge log")
        print("2. Apply merge log")
        action = int(input(""))

        if action == 1:
            generate_merge_log(dst_file, src_file)
        elif action == 2:
            apply_merge_log(dst_file, src_file)

