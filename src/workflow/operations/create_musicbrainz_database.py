import os
import subprocess
from pathlib import Path
from typing import Generator

import orjson
from tqdm import tqdm

from src.core.basemodels import Album
from src.core.logger import logger, lprint
from src.lang import MESSAGE
from scraper.musicbrainz_scraper import MusicBrainzScraper
from src.scraper.musicbrainz_database import MusicBrainzDatabase
from src.workflow.common import easy_linput

OPERATION_NAME = MESSAGE.WF_20251204_194120


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
    
    albums = MusicBrainzScraper._build_album_from_release(release)

    return albums


def main():
    lprint(MESSAGE.WF_20251204_194121)

    parent_directory: Path = easy_linput(MESSAGE.WF_20251204_194122, return_type=Path)
    tar_exe = easy_linput(MESSAGE.WF_20251204_194123, return_type=str)

    recording_tar, release_tar = parent_directory / "recording.tar.xz", parent_directory / "release.tar.xz"

    # 错误 保存 文件
    failed_release_wf = (parent_directory / "failed_release.jsonl").open("a", encoding="utf-8")

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
            failed_release_wf.write(orjson.dumps(release).decode("utf-8") + "\n")
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


