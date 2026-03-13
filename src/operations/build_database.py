from datetime import datetime
from pathlib import Path
import itertools
from concurrent.futures import ThreadPoolExecutor

from tqdm import tqdm

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


def _crawl_vgmdb() -> None:
    rawdir = Path(g_settings.TMP_DIRECTORY, "VGMdb Raw")
    rawdir.mkdir(parents=True, exist_ok=True)

    scraper = VGMdbScraper()
    latest_id = int(scraper.get_latest_album_id())

    pool = ThreadPoolExecutor()
    pbar = tqdm(total=latest_id, desc="Crawl VGMdb", miniters=0)

    def _crawl(a_id: str) -> None:
        url = scraper.ALBUM_PAGE_URL.format(a_id)
        file = Path(rawdir, legalize_filename(url)+".html")
        if file.is_file():
            pbar.update(1)
            return
        try:
            url, content = scraper.get_album_page_content(a_id)
            file.write_text(content, encoding="utf-8")
        except Exception as e:
            logger.error("", exc_info=1)
            raise e
        pbar.update(1)

    list(pool.map(_crawl, map(str, range(1, latest_id+1))))

    pool.shutdown()
    pbar.close()
    scraper.close()


def _builld_vgmdb_database() -> None:
    scraper = VGMdbScraper()
    latest_id = int(scraper.get_latest_album_id())

    pool = ThreadPoolExecutor()
    pbar = tqdm(total=latest_id, desc="VGMdb", miniters=0)

    def _get_album(a_id: str) -> list[Album]:
        try:
            albums = scraper.get_albums(a_id)
        except Exception as e:
            logger.error("", exc_info=1)
            raise e
        pbar.update(1)

    for batch in itertools.batched(map(str, range(1, latest_id+1)), 10):
        list(pool.map(_get_album, batch))
        scraper.close()
        scraper = VGMdbScraper()

    pool.shutdown()
    pbar.close()
    scraper.close()






_crawl_vgmdb()














