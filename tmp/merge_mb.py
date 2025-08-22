import sys
import json
import os
import re
import itertools
import shutil
from difflib import SequenceMatcher
from typing import Generator
from pathlib import Path
import tomllib

import mutagen
from mutagen.flac import FLAC
from mutagen.mp3 import EasyMP3
from mutagen.id3 import ID3

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.logger import logger
from src.common.constants import METADATA_PATH, TMP_PATH
from src.common.json_encoder import CustomJSONEncoder
from src.metadata_source.musicbrainz_api import MusicBrainzAPI
from src.metadata_source.musicbrainz_database import MusicBrainzDatabase
from src.common.basemodels import Album, Track
from src.ongaku_library.ongaku_library import (dump_album_json, album_filename, OngakuScanner, 
    load_album_json, AUDIO_EXTS)
from src.common.utils import dump_toml






if __name__ == "__main__":

    

    tmpdir = Path(r"D:\tmp偶像大师")
    groups = json.loads(Path(r"D:\tmp偶像大师\group.json").read_text(encoding="utf-8"))
    groups = {g[0]: g[1] for g in groups}

    pending_file = Path(r"D:\ongaku-pending\THE IDOLM@STER.toml")
    albums  = list(map(Album.from_dict, tomllib.loads(pending_file.read_text(encoding="utf-8")).values()))

    for album in albums:

        key = os.path.join("vgmdb", album_filename(album)+".json")

        if key not in groups:
            continue

        mb_album = load_album_json(Path(tmpdir, groups[key]))

        if not album.catalognumber and mb_album.catalognumber:
            album.catalognumber = mb_album.catalognumber
        
        if not album.date and mb_album.date:
            album.date = mb_album.date

        if mb_album.tracks:
            album.tracks = mb_album.tracks

        album.links = album.links + mb_album.links

        
    obj = {str(i+1): a.to_dict() for i, a in enumerate(albums)}
    dump_toml(obj, pending_file)

