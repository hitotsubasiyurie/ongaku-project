import sys
import json
import orjson
import pickle
import os
import itertools
from pathlib import Path
from collections import defaultdict

sys.path.append(r"E:\my\ongaku")
os.environ["ONGAKU_TMP_PATH"] = r"E:\ongaku-tmp"


from src.logger import logger
from src.metadata_source.vgmdb_api import VGMdbAPI
from src.metadata_source.musicbrainz_api import MusicBrainzAPI
from src.ongaku_library.basemodels import Album, metadata_filename, save_metadata, load_metadata


if __name__ == "__main__":

    parent_dir = Path(r"E:\ongaku-tmp\vgmdb2")

    for file in parent_dir.rglob("*.json"):
        file.rename(file.parent / metadata_filename(load_metadata(file)))


