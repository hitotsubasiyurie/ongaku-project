import sys
import json
import os
import re
import itertools
import shutil
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
from src.basemodels import Album, Track
from src.ongaku_library.ongaku_library import (dump_album_model, album_filename, OngakuScanner, 
    load_album_model, AUDIO_EXTS)



pending_dir = Path(r"D:\ongaku-pending")
metadata_dir = Path(r"D:\ongaku-metadata")

link_file = pending_dir / "link.json"
link = json.loads(link_file.read_text(encoding="utf-8"))


mdfs = set(os.path.join("vgmdb", f.name) for f in metadata_dir.glob("*.json"))

sum = 0
for group in link:

    if not ( f:= mdfs.intersection(group)):
        continue

    sum += 1
    
print(sum)
        
