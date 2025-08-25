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

from src.logger import logger
from src.common.constants import METADATA_PATH, TMP_PATH
from src.metadata_source.musicbrainz_api import MusicBrainzAPI
from src.metadata_source.musicbrainz_database import MusicBrainzDatabase
from src.common.basemodels import Album, Track
from src.utils import legalize_filename
from src.ongaku_library.ongaku_library import (dump_album_json, album_filename, OngakuScanner, 
    load_album_json, AUDIO_EXTS, ALBUM_FILENAME, TRACK_FILENAME)



if __name__ == "__main__":

    name = "pposjdfsaodpfjsdpfs"*255 + ".flac"
    print(legalize_filename(name))
    print(len(legalize_filename(name)))



# 1. 音轨数完全相同
# 2. 没有音频的文件夹删掉
# 3. 不嵌套的文件夹 认为是专辑文件夹

