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

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.logger import logger
from src.common.constants import METADATA_PATH, TMP_PATH
from src.metadata_source.musicbrainz_api import MusicBrainzAPI
from src.metadata_source.musicbrainz_database import MusicBrainzDatabase
from src.common.basemodels import Album, Track
from src.common.utils import read_standard_tags
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


# 缓存
@cache
def analyze_resource_track(audio: str) -> Track:
    audio = Path(audio)

    tags = read_standard_tags(audio)
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

    tags = read_standard_tags(audios[0])
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


def count_track_similarity(a: Track, b: Track) -> float:
    ratio = SequenceMatcher(None, f"{a.tracknumber}. {a.title}", f"{b.tracknumber}. {b.title}").ratio()
    if a.artist and b.artist:
        ratio += SequenceMatcher(None, a.artist, b.artist).ratio()

    return ratio


def count_album_similarity(a: Album, b: Album, ) -> float:
    ratio = (SequenceMatcher(None, a.catalognumber, b.catalognumber).ratio() + 
             SequenceMatcher(None, a.date, b.date).ratio() + 
             SequenceMatcher(None, a.album, b.album).ratio() + 
             SequenceMatcher(None, MusicBrainzDatabase._abstract_tracks(a), 
                             MusicBrainzDatabase._abstract_tracks(b)).ratio())

    return ratio


def generate_match_log(parent_resource: Path, resource_save_dir: Path, matching_log: Path, show_detail: bool) -> None:
    content = ""

    # 不嵌套的文件夹 认为是专辑文件夹
    resource_directorys = [d for d in parent_resource.rglob("*") 
                           if d.is_dir() and all(f.is_file() for f in d.glob("*"))]
    
    resource_albums = list(map(analyze_resource_album, resource_directorys))

    for res_dir, res_album in zip(resource_directorys, resource_albums):

        # 筛选 tracks 数量一致，再进行匹配
        to_search_albums = [a for a in theme_albums if len(res_album.tracks) == len(a.tracks)] or theme_albums
        match_album = max(to_search_albums, key=lambda a: count_album_similarity(res_album, a))

        audios = list(itertools.chain.from_iterable(res_dir.rglob(f"*{ext}") for ext in AUDIO_EXTS))
        res_tracks = list(map(analyze_resource_track, audios))

        sim_matrix = [[count_track_similarity(ta, tb) for tb in match_album.tracks] 
                        for ta in res_tracks]
        sim_matrix = numpy.asarray(sim_matrix)
        row_ind, col_ind = linear_sum_assignment(sim_matrix, maximize=True)
        track_similarity = sim_matrix[row_ind, col_ind].sum() / len(row_ind)

        lines = []
        lines.append(ALBUM_SIMILARITY + str(count_album_similarity(res_album, match_album))[:5])
        lines.append(TRACK_SIMILARITY + str(track_similarity)[:5])
        lines.append("")
        lines.append(RESOURCE_DIRECTORY_ + str(res_dir))
        lines.append(DESTINATE_DIRECTORY + str(resource_save_dir / album_filename(match_album)))
        show_detail and lines.append(RESOURCE_ALBUM + json.dumps([res_album.catalognumber, res_album.date, res_album.album, len(res_album.tracks)], ensure_ascii=False))
        show_detail and lines.append(MATCHING_ALBUM + json.dumps([match_album.catalognumber, match_album.date, match_album.album, len(match_album.tracks)], ensure_ascii=False))
        lines.append("")
        match_track_names = track_filenames(match_album)
        for row, col in zip(row_ind, col_ind):
            lines.append(RESOURCE_AUDIOFILE_ + audios[row].name)
            lines.append(DESTINATE_AUDIOFILE + match_track_names[col])
            show_detail and lines.append(RESOURCE_TRACK + json.dumps(res_tracks[row].to_tuple(), ensure_ascii=False))
            show_detail and lines.append(MATCHING_TRACK + json.dumps(match_album.tracks[col].to_tuple(), ensure_ascii=False))
            lines.append("")

        content += SEPERATE.join(lines)
    
    matching_log.write_text(content, encoding="utf-8")


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

