import sys
import json
import orjson
import pickle
import os
import itertools
from pathlib import Path
from collections import defaultdict

# sys.path.append(r"E:\my\ongaku")
# os.environ["ONGAKU_TMP_PATH"] = r"E:\ongaku-tmp"


from ..src.logger import logger
from ..src.metadata.vgmdb_api import VGMdbAPI
from ..src.metadata.musicbrainz_api import MusicBrainzAPI
from ..src.ongaku_library.basemodels import Album

if __name__ == "__main__":

    vgmdb_dir = Path(r"E:\ongaku-tmp2\vgmdb")
    resource_dir = Path(r"E:\ongaku-tmp2\resource")
    print(vgmdb_dir)

    # resource_dir.mkdir(parents=True, exist_ok=True)

    # for file in vgmdb_dir.rglob("*.json"):
    #     (resource_dir / os.path.splitext(metadata_filename(load_metadata(file)))[0]).mkdir()


