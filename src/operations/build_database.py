from datetime import datetime
from pathlib import Path
import itertools
from concurrent.futures import ThreadPoolExecutor
from threading import Thread

from tqdm import tqdm
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TaskProgressColumn, MofNCompleteColumn

from src.core.console import cprint, easy_cinput
from src.core.i18n import g_message
from src.core.logger import logger
from src.core.settings import g_settings
from src.core.storage import dump_albums_to_toml, load_albums_from_toml
from src.core.basemodels import Album
from src.scraper import VGMdbScraper, MusicBrainzScraper, DoujinMusicInfoScraper, LastFMScraper
from src.external import init_pgdata, pg_ctl_start, pg_ctl_stop
from src.scraper.musicbrainz_database import MusicBrainzDatabase
from src.utils import legalize_filename

OPERATION_TITLE = g_message.OP_20260312_145800


def _crawl_vgmdb(progress: Progress) -> None:
    rawdir = Path(g_settings.TMP_DIRECTORY, "vgmdb.net", "album")
    rawdir.mkdir(parents=True, exist_ok=True)

    scraper = VGMdbScraper()
    latest_id = int(scraper.get_latest_album_id())

    pool = ThreadPoolExecutor()
    task_id = progress.add_task(f"vgmdb.net", total=latest_id)

    def _crawl(a_id: str) -> None:
        file = Path(rawdir, f"{a_id}.html")
        if file.is_file():
            progress.advance(task_id, 1)
            return
        try:
            content = scraper.get_album_page_content(a_id)
            file.write_text(content, encoding="utf-8")
        except Exception as e:
            logger.error("", exc_info=1)
            raise e
        progress.advance(task_id, 1)

    list(pool.map(_crawl, map(str, range(1, latest_id+1))))

    pool.shutdown()
    scraper.close()


def _crawl_doujinmusicinfo(progress: Progress) -> None:
    rawdir = Path(g_settings.TMP_DIRECTORY, "dojin-music.info", "cd")
    rawdir.mkdir(parents=True, exist_ok=True)

    scraper = DoujinMusicInfoScraper()
    latest_id = int(scraper.get_latest_cd_id())

    pool = ThreadPoolExecutor()
    task_id = progress.add_task(f"dojin-music.info", total=latest_id)

    def _crawl(cd_id: str) -> None:
        file = Path(rawdir, f"{cd_id}.html")
        if file.is_file():
            progress.advance(task_id, 1)
            return
        try:
            content = scraper.get_cd_page_content(cd_id)
            file.write_text(content, encoding="utf-8")
        except Exception as e:
            logger.error("", exc_info=1)
            raise e
        progress.advance(task_id, 1)

    list(pool.map(_crawl, map(str, range(1, latest_id+1))))

    pool.shutdown()


def build_database():

    # 爬网站
    progress = Progress(TextColumn("{task.description}"), BarColumn(), MofNCompleteColumn(), 
                        TimeElapsedColumn())
    with progress:
        crawl_threads = [
            Thread(target=_crawl_vgmdb, args=(progress, ), daemon=True),
            Thread(target=_crawl_doujinmusicinfo, args=(progress, ), daemon=True),
        ]
        [t.start() for t in crawl_threads]
        [t.join() for t in crawl_threads]


build_database()










