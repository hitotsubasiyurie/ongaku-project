import sys
import json
import os
import re
import itertools
from difflib import SequenceMatcher
from typing import Generator
from pathlib import Path
import tomllib
from functools import cache

import mutagen
from mutagen.flac import FLAC
from mutagen.mp3 import EasyMP3
from mutagen.id3 import ID3
import numpy
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.logger import logger
from src.common.constants import METADATA_PATH, TMP_PATH
from src.metadata_source.musicbrainz_api import MusicBrainzAPI
from src.metadata_source.musicbrainz_database import MusicBrainzDatabase
from src.common.basemodels import Album, Track
from src.ongaku_library.ongaku_library import (dump_album_json, album_filename, OngakuScanner, 
    load_album_json, AUDIO_EXTS)


TAGMAP_FLAC = {"catalognumber": "CATALOGNUMBER", "date": "DATE", "album": "ALBUM", 
               "tracknumber": "TRACKNUMBER", "title": "TITLE", "artist": "ARTIST"}
TAGMAP_MP3 = {"catalognumber": "catalognumber", "date": "date", "album": "album", 
              "tracknumber": "tracknumber", "title": "title", "artist": "artist"}


def read_standard_tags(audio: str) -> dict:
    audio = Path(audio)
    if audio.suffix == ".flac":
        _map = TAGMAP_FLAC
        tags = FLAC(audio).tags
    elif audio.suffix == ".mp3":
        _map = TAGMAP_MP3
        tags = EasyMP3(audio).tags
    standard_tags = {s_k: "//".join(tags.get(k, [])) for s_k, k in _map.items()}
    return standard_tags


@cache
def analyze_audio(audio: str) -> Track:
    audio = Path(audio)

    tags = read_standard_tags(audio)
    tracknumber, title, artist = [tags[k] or "" for k in ["tracknumber", "title", "artist"]]

    if not all([tracknumber, title]):
        if match := re.search(r"^(\d+).\s*(.+)$", audio.name):
            if not tracknumber: tracknumber = int(match.group(1))
            if not title: title = match.group(2)
    
    if not title: title = audio.name
    
    return Track(tracknumber=tracknumber or None, title=title, artist=artist)


def analyze_directory(directory: str) -> Album:
    """
    :param directory: 扁平专辑目录
    """
    directory = Path(directory)
    audios = itertools.chain.from_iterable(directory.rglob(f"*{ext}") for ext in AUDIO_EXTS)

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

    date = date.replace(".", "-")
    album_model = Album(catalognumber=catalognumber, date=date, album=album, 
                        tracks=list(sorted([analyze_audio(a) for a in audios], key=lambda a: a.tracknumber)))
    return album_model


def count_track_similarity(a: Track, b: Track) -> float:
    ratio = SequenceMatcher(None, f"{a.tracknumber}. {a.title}", f"{b.tracknumber}. {b.title}").ratio()
    if a.artist and b.artist:
        ratio += SequenceMatcher(None, a.artist, b.artist).ratio()

    return ratio


def count_album_similarity(a: Album, b: Album) -> float:
    ratio = (SequenceMatcher(None, a.catalognumber, b.catalognumber).ratio() + 
             SequenceMatcher(None, a.date, b.date).ratio() + 
             SequenceMatcher(None, a.album, b.album).ratio() + 
             SequenceMatcher(None, MusicBrainzDatabase._abstract_tracks(a), 
                             MusicBrainzDatabase._abstract_tracks(b)).ratio())

    return ratio


if __name__ == "__main__":

    pending_file = Path(r"D:\ongaku-pending\THE IDOLM@STER.toml")
    dst_albums = list(map(Album.from_dict, tomllib.loads(pending_file.read_text(encoding="utf-8")).values()))

    parent_directory = Path(r"D:\移动云盘同步盘")

    # 不嵌套的文件夹 认为是专辑文件夹
    src_directorys = [d for d in parent_directory.rglob("*") 
                        if d.is_dir() and all(f.is_file() for f in d.glob("*"))]
    src_albums = list(analyze_directory(d) for d in src_directorys)

    for src_dir, src_album in zip(src_directorys, src_albums):

        dst_album = max(dst_albums, key=lambda a: count_album_similarity(src_album, a) if len(src_album.tracks) == len(a.tracks) else 0)

        audios = itertools.chain.from_iterable(src_dir.rglob(f"*{ext}") for ext in AUDIO_EXTS)



# 1. 音轨数完全相同
# 2. 没有音频的文件夹删掉
# 3. 不嵌套的文件夹 认为是专辑文件夹
# 4. 考虑重复资源：一个一个文件夹处理
# 5. 考虑已归档资源

