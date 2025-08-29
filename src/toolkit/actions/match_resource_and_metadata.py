import re
import os
import sys
import time
import shutil
import itertools
from pathlib import Path
from functools import cache

import orjson
from tqdm import tqdm
from munkres import Munkres

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils import read_audio_tags
from src.logger import logger, lprint
from src.toolkit.message import MESSAGE
from src.toolkit.toolkit_utils import easy_linput
from src.basemodels import Album, Track, _validate_strtuple
from src.basemodel_utils import (count_album_similarity, count_track_similarity, album_to_unique_str, 
                                        track_to_unique_str)
from src.toolkit.metadata_source.musicbrainz_database import MusicBrainzDatabase
from src.repository.ongaku_repository import (dump_albums_to_toml, load_albums_from_toml, AUDIO_EXTS, album_filename, 
                                              track_filenames)


SEPERATE = f"{'-'*16} seperate {'-'*16}"

NO_APPLY = "[_NO_APPLY_]"
YES_APPLY = "[_YES_APPLY_]"

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


def generate_match_log() -> None:

    # input 输入
    metadata_file = input(f"Please input a metadata file: ").strip("'\"")
    old_parent_dir = input(f"Please input old resource parent directory: ").strip("'\"")
    new_parent_dir = input(f"Please input new resource parent directory: ").strip("'\"")

    if not all([metadata_file, old_parent_dir, new_parent_dir]):
        return

    metadata_file, old_parent_dir, new_parent_dir = Path(metadata_file), Path(old_parent_dir), Path(new_parent_dir)

    match_log = metadata_file.parent / "match.log"
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

        # 单体相似度 最大 匹配 album
        match_album = max(to_search_albums, key=lambda a: count_album_similarity(res_album, a))

        # 总和相似度 最大 匹配 tracks
        audios = list(itertools.chain.from_iterable(res_dir.rglob(f"*{ext}") for ext in AUDIO_EXTS))
        res_tracks = list(map(analyze_resource_track, audios))

        m = Munkres()
        matrix = [[-count_track_similarity(ta, tb) for tb in match_album.tracks]
                   for ta in res_tracks]
        indexes = m.compute(matrix)
        track_similarity = sum(-matrix[row][col] for row, col in indexes) / len(indexes)

        lines = []
        lines.append("")
        lines.append(NO_APPLY)
        lines.append(ALBUM_SIMILARITY + format(count_album_similarity(res_album, match_album), '.2f'))
        lines.append(TRACK_SIMILARITY + format(track_similarity, '.2f'))
        lines.append("")
        lines.append(OLD_DIRECTORY + str(res_dir))
        lines.append(NEW_DIRECTORY + str(new_parent_dir / album_filename(match_album)))
        lines.append("")
        lines.append(RESOURCE_ALBUM + album_to_unique_str(res_album))
        lines.append(MATCHING_ALBUM + album_to_unique_str(match_album))
        lines.append("")
        match_track_names = track_filenames(match_album)
        for row, col in indexes:
            lines.append(OLD_AUDIOFILE + audios[row].name)
            lines.append(NEW_AUDIOFILE + match_track_names[col] + audios[row].suffix.lower())
            lines.append(RESOURCE_TRACK + track_to_unique_str(res_tracks[row]))
            lines.append(MATCHING_TRACK + track_to_unique_str(match_album.tracks[col]))
            lines.append("")

        content += "\n" + SEPERATE + "\n".join(lines) + "\n"
    
    match_log.write_text(content, encoding="utf-8")


def apply_match_log() -> None:
    match_log = input(f"Please input match log: ").strip("'\"")

    if not match_log:
        return
    
    match_log = Path(match_log)

    for line in match_log.read_text(encoding="utf-8").split("\n"):
        if line.startswith(SEPERATE):
            apply, old_dir, new_dir, old_file, new_file = [None] * 5
        elif line.startswith(YES_APPLY):
            apply = True
        elif line.startswith(OLD_DIRECTORY):
            old_dir = line.removeprefix(OLD_DIRECTORY)
        elif line.startswith(NEW_DIRECTORY):
            new_dir = line.removeprefix(NEW_DIRECTORY)
            if apply:
                os.makedirs(new_dir, exist_ok=True)
        elif line.startswith(OLD_AUDIOFILE):
            old_file = line.removeprefix(OLD_AUDIOFILE)
        elif line.startswith(NEW_AUDIOFILE):
            new_file = line.removeprefix(NEW_AUDIOFILE)
            if not apply:
                continue
            # 开始应用
            old, new = Path(old_dir, old_file), Path(new_dir, new_file)
            # TODO: 不同格式可能并存
            not new.exists() and old.rename(new)


def clean_old_parent_dir() -> None:
    old_parent_dir = input(f"Please input old resource parent directory: ").strip("'\"")

    if not all([old_parent_dir]):
        return
    
    old_parent_dir = Path(old_parent_dir)

    # 从下往上 删除 没有音频文件的 目录
    for d in reversed(list(filter(Path.is_dir, old_parent_dir.rglob("*")))):
        if not list(itertools.chain.from_iterable(d.rglob(f"*{ext}") for ext in AUDIO_EXTS)):
            shutil.rmtree(d)


def match_resource_and_metadata():

    # 循环交互
    while True:

        print("Please input action number:")
        print("1. Generate match log")
        print("2. Apply match log")
        print("3. Clean old resource parent directory")
        action = int(input(""))

        if action == 1:
            generate_match_log()
        elif action == 2:
            apply_match_log()
        elif action == 3:
            clean_old_parent_dir()




