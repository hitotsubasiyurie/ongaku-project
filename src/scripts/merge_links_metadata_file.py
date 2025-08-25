import os
import sys
import time
from pathlib import Path

import orjson
from tqdm import tqdm
import numpy
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.logger import logger, _ongaku_logger
from src.common.basemodels import Album
from src.common.basemodel_utils import count_album_similarity, album_to_unique_str
from src.metadata_source.musicbrainz_database import MusicBrainzDatabase
from src.repository.ongaku_repository import dump_albums_to_toml, load_albums_from_toml


SEPERATE = f"\n{'-'*16} seperate {'-'*16}\n"

SIMILARITY = "SIMILARITY: "

DST_ALBUM = "DST_ALBUM: "
SRC_ALBUM = "SRC_ALBUM: "
YES_MERGE = "YES_MERGE: "


def generate_match_log(dst_file: Path, src_file: Path, match_log: Path) -> None:
    content = ""

    skip_keyword = input("Please input link keyword to skip (such as 'musicbrainz') (default None): ").strip() or None
    min_sim = float(input("Please input similarity threshold (default 0.1): ").strip() or 0)
    enable_catno_filter = (input("Please input if filter catalognumber (Y/N) (default Y): ").strip() or "Y") == "Y"

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

    print("Matching the most similar album...")
    row_ind, col_ind = linear_sum_assignment(sim_matrix, maximize=True)

    for row, col in zip(row_ind, col_ind):

        lines = []
        lines.append(SIMILARITY + format(sim_matrix[row][col], '.2f'))
        lines.append("")
        lines.append(DST_ALBUM + album_to_unique_str(dst_albums[row]))
        lines.append(SRC_ALBUM + album_to_unique_str(src_albums[col]))
        
        content += SEPERATE + "\n".join(lines)

    match_log.write_text(content, encoding="utf-8")


if __name__ == "__main__":

    # input 输入

    dst_file = input(f"Please input dst metadata file (merge to): ").strip("'\"")
    src_file = input(f"Please input src metadata file (merge from): ").strip("'\"")

    if not src_file or not dst_file:
        sys.exit(0)

    src_file, dst_file = Path(src_file), Path(dst_file)

    match_log = dst_file.parent / "match.log"

    # 日志输出至目录
    if not _ongaku_logger.outfile:
        _ongaku_logger.set_outfile(dst_file.parent)

    # 循环交互
    # 可以一批一批地合并
    # 合并后 删除 src albums 
    while True:

        os.system("cls")
        print("Please input action number：")
        print("1. Generate match log")
        action = int(input(""))

        if action == 1:
            generate_match_log(dst_file, src_file, match_log)


