"""
处理 MusicBrainz JSON Data Dumps

1. 下载 recording.tar.xz, release.tar.xz
    https://metabrainz.org/datasets/download


"""

import os
import sys
from datetime import datetime
import subprocess
from pathlib import Path
from typing import Generator

import orjson
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.logger import logger, _ongaku_logger
from src.metadata_source.musicbrainz_api import MusicBrainzAPI
from src.metadata_source.musicbrainz_database import MusicBrainzDatabase
from src.common.basemodels import Album


def read_musicbrainz_tar_dump(tar_exe: str, tar_file: str) -> Generator[str, None, None]:
    tar_file = str(tar_file)
    x = os.path.basename(tar_file).split(".")[0]
    posix_path = "/" + tar_file.replace(":", "").replace("\\", "/")
    cmd = [tar_exe, "-xOf", posix_path, f"mbdump/{x}"]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")

    for line in process.stdout:
        yield line


def release_to_albums(recordings: dict, release: dict) -> list[Album]:
    for media in release["media"]:
        for track in media.get("tracks", []):
            track["recording"].update(recordings.get(track["recording"]["id"], {}))
    
    albums = MusicBrainzAPI._build_album_from_release(release)

    return albums


if __name__ == "__main__":

    # input 输入

    parent_directory = input(f"Please input dump files' directory: ").strip("'\"")
    tar_exe  = input(f"Please input tar.exe path: ").strip("'\"")

    if not parent_directory or not tar_exe:
        sys.exit(0)

    parent_directory = Path(parent_directory)
    recording_tar, release_tar = parent_directory / "recording.tar.xz", parent_directory / "release.tar.xz"

    # 日志输出至文件
    if not _ongaku_logger.outfile:
        _ongaku_logger.set_outfile(parent_directory / f"{datetime.now().strftime("%Y-%d-%m-%H-%M-%S")}.log")

    # 错误 保存 文件
    wrong_release_wf = (parent_directory / "wrong_release.jsonl").open("a", encoding="utf-8")

    # 断点 续作 文件
    checkpoint_file = parent_directory / "checkpoint"
    checkpoint = int(checkpoint_file.read_text()) if checkpoint_file.exists() else -1

    recordings = {r["id"]: r for r in map(orjson.loads, read_musicbrainz_tar_dump(tar_exe, recording_tar))}

    db = MusicBrainzDatabase()

    pbar = tqdm(total=5*100*10000)
    rid_batch, album_batch = [], []
    for n, line in enumerate(read_musicbrainz_tar_dump(tar_exe, release_tar)):

        # 跳过断点
        if n <= checkpoint:
            continue

        release = orjson.loads(line)

        try:
            albums = release_to_albums(recordings, release)
        except Exception as e:
            print(e)
            logger.error("", exc_info=1)
            wrong_release_wf.write(orjson.dumps(release).decode("utf-8") + "\n")
            continue
        
        rid_batch.extend([release["id"]] * len(albums))
        album_batch.extend(albums)
        
        # 批量入库
        if len(rid_batch) > 1000:
            db.insert_albums(rid_batch, album_batch)
            pbar.n = n
            pbar.refresh()
            rid_batch, album_batch = [], []
            # 更新 检查点
            checkpoint_file.write_text(str(n))


