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
import time
import pickle
from pathlib import Path
from collections import defaultdict

import orjson
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.metadata_source.vgmdb_api import VGMdbAPI
from src.metadata_source.musicbrainz_api import MusicBrainzAPI
from src.basemodels import Album


if __name__ == "__main__":

    directory = Path(input("输入父目录路径：").strip("'\""))
    recording_db, release_db = directory / "recording", directory / "release"

    album_db, album_index = directory / "album", directory / "album.index"

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

    rid2pos = defaultdict(list)
    rf = release_db.open("rb")
    wf = album_db.open("w", encoding="utf-8")

    for release in map(orjson.loads, rf):
        for a in _to_albums(release):
            start = wf.tell()
            wf.write(a.model_dump_json() + "\n")
            end = wf.tell()
            rid2pos[release["id"]].append((start, end))
        # 每 5 秒刷新
        if not int(time.time()) % 5:
            wf.flush()
            pbar.n = rf.tell()
            pbar.refresh()
    
    rf.close()
    wf.close()

    album_index.write_bytes(pickle.dumps(rid2pos))

