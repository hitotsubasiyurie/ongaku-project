import re
import os
import sys
import time
import itertools
from pathlib import Path
from functools import cache

import orjson
from tqdm import tqdm
import numpy
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils import read_audio_tags
from src.logger import logger, _ongaku_logger
from src.common.basemodels import Album, Track, _validate_strtuple
from src.common.basemodel_utils import (count_album_similarity, count_track_similarity, album_to_unique_str, 
                                        track_to_unique_str)
from src.metadata_source.musicbrainz_database import MusicBrainzDatabase
from src.repository.ongaku_repository import (dump_albums_to_toml, load_albums_from_toml, AUDIO_EXTS, album_filename, 
                                              track_filenames)


SEPERATE = f"\n{'-'*16} seperate {'-'*16}\n"

ALBUM_SIMILARITY = "ALBUM_SIMILARITY: "
TRACK_SIMILARITY = "TRACK_SIMILARITY: "

OLD_DIRECTORY = "OLD_DIRECTORY: "
NEW_DIRECTORY = "NEW_DIRECTORY: "

RESOURCE_ALBUM = "RESOURCE_ALBUM: "
MATCHING_ALBUM = "MATCHING_ALBUM: "

OLD_AUDIOFILE = "OLD_AUDIOFILE: "
NEW_AUDIOFILE = "NEW_AUDIOFILE: "
RESOURCE_TRACK = "RESOURCE_TRACK: "
MATCHING_TRACK = "MATCHING_TRACK: "



# 缓存
@cache
def analyze_resource_track(audio: str) -> Track:
    audio = Path(audio)

    tags = read_audio_tags(audio)
    tracknumber, title, artist = [tags[k] or "" for k in ["tracknumber", "title", "artist"]]

    if not all([tracknumber, title]):
        if match := re.search(r"^(\d+).\s*(.+)$", audio.name):
            # 空字符 或 包含其他非数字
            if not tracknumber.isdigit(): tracknumber = match.group(1)
            if not title: title = match.group(2)
    
    if not title: title = audio.name
    tracknumber = int(tracknumber) if tracknumber.isdigit() else None
    
    return Track(tracknumber=tracknumber, title=title, artist=artist)


def analyze_resource_album(directory: str) -> Album:
    """
    :param directory: 扁平专辑目录
    """
    directory = Path(directory)
    audios = list(itertools.chain.from_iterable(directory.rglob(f"*{ext}") for ext in AUDIO_EXTS))

    tags = read_audio_tags(audios[0])
    catalognumber, date, album = [tags[k] or "" for k in ["catalognumber", "date", "album"]]
    
    if match := re.search(r"^\[([A-Z0-9-]+)\]\s+\[([0-9.-]+)\]\s+(.+)$", directory.name):
        if not catalognumber: catalognumber = match.group(1)
        if not date or len(date) < len(match.group(2)): date = match.group(2)
        if not album: album = match.group(3)
    if match := re.search(r"^\[([0-9.-]+)\]\s+(.+)$", directory.name):
        if not date or len(date) < len(match.group(1)): date = match.group(1)
        if not album: album = match.group(2)
    if not album: album = directory.name

    # date 字段替换常见字符
    date = re.sub(r"[./]", "-", date)
    album_model = Album(catalognumber=catalognumber, date=date, album=album, 
                        tracks=list(sorted([analyze_resource_track(a) for a in audios], key=lambda a: a.tracknumber)))
    return album_model


def generate_match_log(metadata_file: Path, old_parent_dir: Path, new_parent_dir: Path, match_log: Path) -> None:
    content = ""

    enable_tracknumber_filter = (input("Please input if filter tracks number (Y/N) (default Y): ").strip() or "Y") == "Y"

    theme_albums = load_albums_from_toml(metadata_file)

    # 不嵌套的文件夹 认为是专辑文件夹
    resource_directorys = [d for d in old_parent_dir.rglob("*") 
                           if d.is_dir() and all(f.is_file() for f in d.glob("*"))]
    
    resource_albums = list(map(analyze_resource_album, resource_directorys))

    for res_dir, res_album in zip(resource_directorys, resource_albums):

        # 筛选 tracks 数量一致
        to_search_albums = [a for a in theme_albums if len(res_album.tracks) == len(a.tracks)] if enable_tracknumber_filter else theme_albums
        if not to_search_albums:
            continue

        match_album = max(to_search_albums, key=lambda a: count_album_similarity(res_album, a))

        audios = list(itertools.chain.from_iterable(res_dir.rglob(f"*{ext}") for ext in AUDIO_EXTS))
        res_tracks = list(map(analyze_resource_track, audios))

        sim_matrix = [[count_track_similarity(ta, tb) for tb in match_album.tracks] 
                        for ta in res_tracks]
        sim_matrix = numpy.asarray(sim_matrix)
        row_ind, col_ind = linear_sum_assignment(sim_matrix, maximize=True)
        track_similarity = sim_matrix[row_ind, col_ind].sum() / len(row_ind)

        lines = []
        lines.append(ALBUM_SIMILARITY + format(count_album_similarity(res_album, match_album), '.2f'))
        lines.append(TRACK_SIMILARITY + format(track_similarity, '.2f'))
        lines.append("")
        lines.append(OLD_DIRECTORY + str(res_dir))
        lines.append(NEW_DIRECTORY + str(old_parent_dir / album_filename(match_album)))
        lines.append("")
        lines.append(RESOURCE_ALBUM + album_to_unique_str(res_album))
        lines.append(MATCHING_ALBUM + album_to_unique_str(match_album))
        lines.append("")
        match_track_names = track_filenames(match_album)
        for row, col in zip(row_ind, col_ind):
            lines.append(OLD_AUDIOFILE + audios[row].name)
            lines.append(NEW_AUDIOFILE + match_track_names[col])
            lines.append(RESOURCE_TRACK + track_to_unique_str(res_tracks[row]))
            lines.append(MATCHING_TRACK + track_to_unique_str(match_album.tracks[col]))
            lines.append("")

        content += SEPERATE + "\n".join(lines)
    
    match_log.write_text(content, encoding="utf-8")


if __name__ == "__main__":

    # input 输入
    metadata_file = input(f"Please input a metadata file: ").strip("'\"")
    old_parent_dir = input(f"Please input old resource parent directory: ").strip("'\"")
    new_parent_dir = input(f"Please input new resource parent directory: ").strip("'\"")

    if not all([metadata_file, old_parent_dir, new_parent_dir]):
        sys.exit(0)

    metadata_file, old_parent_dir, new_parent_dir = Path(metadata_file), Path(old_parent_dir), Path(new_parent_dir)

    match_log = metadata_file.parent / "match.log"

    # 日志输出至目录
    if not _ongaku_logger.outfile:
        _ongaku_logger.set_outfile(metadata_file.parent)

    # 循环交互
    while True:

        print("Please input action number:")
        print("1. Generate match log")
        print("2. Apply match log")
        action = int(input(""))

        if action == 1:
            generate_match_log(metadata_file, old_parent_dir, new_parent_dir)
        elif action == 2:
            apply_match_log(dst_file, src_file, merge_log)




