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

    # pending_file = Path(r"D:\ongaku-pending\THE IDOLM@STER pending - 副本.json")
    # pending_data = json.loads(pending_file.read_text(encoding="utf-8"))

    # new_pending = []

    # for value in pending_data:

    #     if isinstance(value, dict):
    #         new_pending.append(value)
    #         continue

    #     d0, d1 = value
    #     d0["tracks"] = d1["tracks"]
    #     d0["links"].extend(d1["links"])
    #     new_pending.append(d0)

    # Path(r"D:\ongaku-pending\THE IDOLM@STER pending - new.json").write_text(json.dumps(new_pending, ensure_ascii=False, indent=2, cls=CustomJSONEncoder), encoding="utf-8")

    # albums = [load_album_json(f) for f in Path(r"D:\ongaku-pending\偶像大师\vgmdb").rglob("*.json")]
    
    # obj = {str(i+1): a.to_dict() for i, a in enumerate(albums)}

    # Path(r"D:\ongaku-pending\pending.toml").write_text(dump_toml(obj), encoding="utf-8")





