"""
处理 MusicBrainz JSON Data Dumps

1. 下载 recording.tar.xz, release.tar.xz
    https://metabrainz.org/datasets/download

2. 解压得到 recording, release
    tar -xf recording.tar.xz
    tar -xf release.tar.xz

3. 处理

4. 得到 album, album.index
    album 是 jsonl 格式，每一行是 Album 对象
    album.index 是 pickle 序列化的 dict[str, list[tuple[int, int]]]

"""

import sys
import csv
import json
import time
import logging
import pickle
from pathlib import Path
from collections import defaultdict

import orjson
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.logger import logger
from src.common.constants import TMP_PATH
from src.metadata_source.vgmdb_api import VGMdbAPI
from src.metadata_source.musicbrainz_api import MusicBrainzAPI
from src.metadata_source.musicbrainz_database import MusicBrainzDatabase
from src.common.basemodels import Album


if __name__ == "__main__":

    # 抑制日志
    not TMP_PATH and logger.setLevel(logging.ERROR)

    directory = Path(input("输入父目录路径：").strip("'\""))
    recording_db, release_db = directory / "recording", directory / "release"
    csv_file = directory / "album.csv"

    with recording_db.open(encoding="utf-8") as f:
        recordings = {r["id"]: r for r in map(orjson.loads, f)}

    def _to_albums(release: dict) -> list[Album]:
        [track["recording"].update(recordings.get(track["recording"]["id"], {}))
            for media in release["media"] for track in media.get("tracks", [])]
        
        link = f"{MusicBrainzAPI._RELEASE_PAGE_URL}/{release['id']}"
        catnos = [l["catalog-number"] for l in release["label-info"] if l["catalog-number"]]
        discs = sorted(MusicBrainzAPI._get_disc_from_release(release), key=lambda d: d.discnumber)

        albums = VGMdbAPI._assemble_albums(catnos, release.get("date", ""), release["title"], discs, link)
        return albums

    pbar = tqdm(total=release_db.stat().st_size, unit='B', unit_scale=True)

    rf = release_db.open("rb")
    wf = csv_file.open("w", encoding="utf-8", newline="")

    writer = csv.DictWriter(wf, fieldnames=MusicBrainzDatabase.COLUMNS, 
                            quoting=csv.QUOTE_STRINGS, extrasaction="ignore")
    writer.writeheader()

    for release in map(orjson.loads, rf):
        for album in _to_albums(release):
            album = album.model_dump()
            album["release_id"] = release["id"]
            album["tracks_json"] = json.dumps(album["tracks"], ensure_ascii=False)
            links_str = ", ".join(album["links"])
            album["links"] = f"{{links_str}}"
            album["_date_min"], album["_date_max"] = MusicBrainzDatabase._date_str_to_range(album["date"])
            album["_tracks_count"] = len(album["tracks"])
            album["_tracks_abstract"] = "\n".join(f'{t["tracknumber"]}. {t["title"]}' for t in album["tracks"])
            writer.writerow(album)
        # 每 5 秒刷新
        if not int(time.time()) % 5:
            pbar.n = rf.tell()
            pbar.refresh()
            wf.flush()
    
    rf.close()
    wf.close()

