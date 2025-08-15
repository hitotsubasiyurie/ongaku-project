

import sys
import os
import json
import csv
from pathlib import Path
import os
from typing import Optional, Union, Generator
import itertools
from pathlib import Path
import uuid
import time
import pickle
import re
import json
from threading import Lock

from ruamel.yaml import YAML
import mutagen
from mutagen.flac import FLAC
from mutagen.mp3 import EasyMP3

sys.path.append(r"E:\my\my-ongaku")

from src.common.exception import OngakuException
from src.common.constants import OngakuConstants
from src.logger import logger
from src.common.utils import legalize_filename, dump_yaml, archive_directory
from src.metadata_source.audiofiles_api import AudioFilesAPI
from src.basemodels import Album, MultiDiscAlbum, Disc, Track


def write_audio_tag(audiopath: str, tag: dict) -> None:
    """
    写音频标签字典。
    raises: OngakuException
    """
    if Path(audiopath).suffix == ".flac":
        audio = FLAC(audiopath)
        audio.clear()
        audio.update(tag)
        audio.save()
    else:
        logger.error(f"Unsupported audio format. {audio.suffix} {audio}")
        raise OngakuException()


def load_album(metafile: str) -> Album:
    cont = Path(metafile).read_text(encoding="utf-8")
    lines = [l for l in cont.split("\n----\n")[0].split("\n") if l.strip()]
    album = Album(**json.loads(lines[0]))
    table = [json.loads(l) for l in lines[1:]]
    tracks = [Track(tracknumber=vals[0], title=vals[1], artist=vals[2]) for vals in table]
    album.tracks = tracks
    return album


def archive_album(metafile: str, album_dir: str) -> None:
    """tracknumber title 完全匹配。"""
    meta_album = load_album(metafile)

    audios = itertools.chain(Path(album_dir).rglob("*.mp3"), Path(album_dir).rglob("*.flac"))
    tags = [AudioFilesAPI.get_audio_tag_standard(a) for a in audios]
    vals = set((tag["tracknumber"], tag["title"]) for tag in tags)
    if not set((str(t.tracknumber), t.title) for t in meta_album.tracks) == vals:
        logger.error(f"Not the same. {vals} {set((t.tracknumber, t.title) for t in meta_album.tracks)}")
        return
    [write_audio_tag(a, t) for a, t in zip(audios, tags)]
    dst = Path(album_dir).parent / legalize_filename(f"{meta_album.catalognumber} {meta_album.date} {meta_album.album}.zip")
    archive_directory(album_dir, dst)



archive_album(r"D:\ヨスガノソラ\KICM-3214 2010-10-27 TVアニメ『ヨスガノソラ』オープニング主題歌 比翼の羽根.jsonl", r"D:\ヨスガノソラ\TVアニメ『ヨスガノソラ』オープニング主題歌 比翼の羽根")

















