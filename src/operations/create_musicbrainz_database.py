import os
import shutil
import subprocess
from pathlib import Path
from typing import Generator

import orjson
from tqdm import tqdm

from src.core.basemodels import Album
from src.core.console import cprint, easy_cinput
from src.core.i18n import g_message
from src.core.logger import logger
from src.core.settings import g_settings
from src.external import pg_ctl_start, pg_ctl_stop, pg_dump_database
from src.scraper.musicbrainz_database import init_musicbrainz_database, MusicBrainzDatabase
from src.scraper.musicbrainz_scraper import MusicBrainzScraper

OPERATION_NAME = g_message.WF_20251204_194120


def read_musicbrainz_tar_dump(tar_file: str) -> Generator[str, None, None]:
    """
    --force-local   归档文件是本地路径
    -x              解压
    -O              解压到标准输出
    -f              指定路径
    """
    tar_exe = os.path.abspath(os.path.join("bin", "tar", "tar.exe"))
    tar_file = str(tar_file)
    x = os.path.basename(tar_file).split(".")[0]
    cmd = [tar_exe, "--force-local", "-xOf", tar_file, f"mbdump/{x}"]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")

    for line in process.stdout:
        yield line


def release_to_albums(recordings: dict, release: dict) -> list[Album]:
    for media in release["media"]:
        for track in media.get("tracks", []):
            track["recording"].update(recordings.get(track["recording"]["id"], {}))
    
    albums = MusicBrainzScraper._build_album_from_release(release)

    return albums


def create_musicbrainz_database():
    cprint(g_message.WF_20251204_194121)

    parent_directory: Path = easy_cinput(g_message.WF_20251204_194122, return_type=Path)

    recording_tar, release_tar = parent_directory / "recording.tar.xz", parent_directory / "release.tar.xz"

    # 错误 保存 文件
    failed_release_wf = (parent_directory / "failed_release.jsonl").open("a", encoding="utf-8")

    # 断点 续作 文件
    checkpoint_file = parent_directory / "checkpoint"
    checkpoint = int(checkpoint_file.read_text()) if checkpoint_file.exists() else -1

    recordings = {r["id"]: r for r in map(orjson.loads, read_musicbrainz_tar_dump(recording_tar))}

    pgdata = os.path.join(g_settings.TMP_DIRECTORY, "musicbrainz_pgdata")
    if os.path.isdir(pgdata):
        if easy_cinput(g_message.WF_20251204_194123, default="N") == "Y":
            shutil.rmtree(pgdata)

    # 初始化数据目录
    init_musicbrainz_database(pgdata)
    cprint(g_message.WF_20251204_194124)

    pg_ctl_start(pgdata)
    cprint(g_message.WF_20251204_194125)

    database = MusicBrainzDatabase()

    pbar = tqdm(total=5*100*10000)
    rid_batch, album_batch = [], []
    for n, line in enumerate(read_musicbrainz_tar_dump(release_tar)):

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
            database.insert_albums(rid_batch, album_batch)
            pbar.n = n
            pbar.refresh()
            rid_batch, album_batch = [], []
            # 更新 检查点
            checkpoint_file.write_text(str(n))

    pbar.close()

    # 备份数据库
    cprint(g_message.WF_20251204_194128)
    dmpfile = os.path.join(g_settings.TMP_DIRECTORY, "musicbrainz.dmp")
    pg_dump_database("musicbrainz", dmpfile)
    cprint(g_message.WF_20251204_194127.format(dmpfile))

    pg_ctl_stop(pgdata)
    cprint(g_message.WF_20251204_194126)

