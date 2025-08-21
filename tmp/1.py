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






def generate_merging_list(pending_dir: str, groups: list[list[str]], filter_files: set[str]) -> list[dict]:
    filter_files = set(filter_files)

    merging_list = []
    for group in groups:

        if filter_files and not filter_files.isdisjoint(group):
            continue

        _dict = {}

        source_names = [os.path.dirname(s) for s in group]
        _maxlen = max(map(len, source_names))
        source_names = [n.ljust(_maxlen) for n in source_names]

        source_albums = [load_album_json(Path(pending_dir, s)) for s in group]

        _dict.update({f"catalognumber {n}": a.catalognumber for n, a in zip(source_names, source_albums) if a.catalognumber})
        _dict.update({f"date {n}": a.date for n, a in zip(source_names, source_albums) if a.catalognumber})
        _dict.update({f"album {n}": a.album for n, a in zip(source_names, source_albums) if a.catalognumber})

        source_tracklists = [a.tracks for a in source_albums]
        for i, source_ts in enumerate(itertools.zip_longest(*source_tracklists, fillvalue=None)):
            _dict.update({f"{i} {n}": [t.tracknumber, t.title, t.artist] for n, t in zip(source_names, source_ts) if t})

        _dict["sources"] = group

        merging_list.append(_dict)

    return merging_list


if __name__ == "__main__":

    # input 输入

    # pending_dir = input(f"Please input pending directory: ").strip("'\"")
    
    # group_file = input(f"Please input group file ({group_file}): ").strip("'\"") or group_file

    # if not pending_dir:
    #     sys.exit(0)

    # group_file = Path(group_file)
    # mgl_file = Path(pending_dir, "merging_list.json")

    # groups = json.loads(group_file.read_text(encoding="utf-8"))
    # merging_list = generate_merging_list(pending_dir, groups, files)

    # mgl_file.write_text(json.dumps(merging_list, indent=2, ensure_ascii=False, cls=CustomJSONEncoder), encoding="utf-8")

    albums = []
    pending_dir = Path(r"D:\ongaku-pending\偶像大师")
    group_file = Path(r"D:\ongaku-pending\偶像大师\group.json")
    groups = json.loads(group_file.read_text(encoding="utf-8"))
    data = []
    _dict = {g[0]: g[1] for g in groups}

    for mdf in Path(r"D:\ongaku-pending\偶像大师\vgmdb").rglob("*.json"):
        mb_mdf = _dict.get(str(mdf.relative_to(pending_dir)))
        if mb_mdf:
            mb_mdf = pending_dir / mb_mdf
            data.append([load_album_json(mdf).to_dict(), load_album_json(mb_mdf).to_dict()])
        else:
            data.append(load_album_json(mdf).to_dict())

    Path(r"D:\ongaku-pending\偶像大师\pending.json").write_text(json.dumps(data, ensure_ascii=False, indent=4, cls=CustomJSONEncoder), encoding="utf-8")





