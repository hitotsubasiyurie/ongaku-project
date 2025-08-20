import sys
import json
import os
import re
import itertools
from difflib import SequenceMatcher
from typing import Generator
from pathlib import Path

import mutagen
from mutagen.flac import FLAC
from mutagen.mp3 import EasyMP3
from mutagen.id3 import ID3

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.logger import logger
from src.common.constants import METADATA_PATH, TMP_PATH
from src.metadata_source.musicbrainz_api import MusicBrainzAPI
from src.metadata_source.musicbrainz_database import MusicBrainzDatabase
from src.common.basemodels import Album, Track
from src.ongaku_library.ongaku_library import (dump_album_model, album_filename, OngakuScanner, 
    load_album_model, AUDIO_EXTS)


def read_standard_tags(audio: str) -> dict:
    if Path(audio).suffix == ".flac":
        _map = {"catalognumber": "CATALOGNUMBER", "date": "DATE", "album": "ALBUM", 
                "tracknumber": "TRACKNUMBER", "title": "TITLE", "artist": "ARTIST"}
        tags = FLAC(audio).tags
        standard_tags = {s_k: "//".join(tags.get(k, [])) for s_k, k in _map.items()}
    elif Path(audio).suffix == ".mp3":
        _map = {"catalognumber": "catalognumber", "date": "date", "album": "album", 
                "tracknumber": "tracknumber", "title": "title", "artist": "artist"}
        tags = EasyMP3(audio).tags
        standard_tags = {s_k: "//".join(tags.get(k, [])) for s_k, k in _map.items()}
    return standard_tags


def analyze_track(audio: str) -> Track:
    audio = Path(audio)
    tags = read_standard_tags(audio)
    tracknumber, title, artist = [tags[k] or "" for k in ["tracknumber", "title", "artist"]]

    if not all([tracknumber, title]) and (match := re.search(r"^(\d+).\s*(.+)$", audio.name)):
        if not tracknumber: tracknumber = int(match.group(1))
        if not title: title = match.group(2)
    if not title: title = audio.name
    
    return Track(tracknumber=tracknumber or None, title=title, artist=artist)


def analyze_album(directory: str) -> Album:
    directory = Path(directory)
    audios = itertools.chain.from_iterable(Path(directory).glob(f"*{ext}") for ext in AUDIO_EXTS)

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
                        tracks=list(sorted([analyze_track(a) for a in audios], key=lambda a: a.tracknumber)))
    return album_model

def count_album_similarity(a: Album, b: Album) -> float:
    ratio = (SequenceMatcher(None, a.catalognumber, b.catalognumber).ratio() + 
             SequenceMatcher(None, a.date, b.date).ratio() + 
             SequenceMatcher(None, a.album, b.album).ratio() + 
             SequenceMatcher(None, MusicBrainzDatabase._abstract_tracks(a), 
                             MusicBrainzDatabase._abstract_tracks(b)).ratio())

    return ratio


if __name__ == "__main__":

    pending_dir = input(f"Please input pending directory: ").strip("'\"")

