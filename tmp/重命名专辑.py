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


from ongaku.logger import logger
from ongaku.metadata.vgmdb_api import VGMdbAPI
from ongaku.metadata.musicbrainz_api import MusicBrainzAPI
from ongaku.common.metadata import Album, metadata_filename, save_metadata, load_metadata


if __name__ == "__main__":

    parent_dir = Path(r"E:\ongaku-tmp\vgmdb2")

    for file in parent_dir.rglob("*.json"):
        file.rename(file.parent / metadata_filename(load_metadata(file)))


