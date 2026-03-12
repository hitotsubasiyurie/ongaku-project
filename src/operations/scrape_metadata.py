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

OPERATION_TITLE = g_message.OP_20260307_103500


def _scrape_vgmdb(urls: list[str], existing_albums: list[Album]) -> list[Album]:
    scraper = VGMdbScraper()

    # 获取 album ids
    a_ids = []
    for url in urls:
        if not url.startswith(VGMdbScraper.ROOT_URL):
            continue
        if "/album/" in url:
            a_ids.append(url.split("/album/")[1].split("/")[0])
        elif "/product/" in url:
            product_id = url.split("/")[-1]
            a_ids.extend(scraper.get_album_ids_from_product(product_id))
        elif "/artist/" in url:
            artist_id = url.split("/")[-1]
            a_ids.extend(scraper.get_album_ids_from_artist(artist_id))
        elif "/search?" in url:
            a_ids.extend(scraper.get_album_ids_from_search_page(url))

    # 过滤 已存在元数据 的 album ids
    existing_a_ids = [link.split("/")[-1] for a in existing_albums for link in a.links if link.startswith(VGMdbScraper.ROOT_URL)]
    a_ids = list(set(a_ids) - set(existing_a_ids))

    if not a_ids:
        return []

    # 开始 获取 元数据

    pool = ThreadPoolExecutor()
    futures = []
    pbar = tqdm(total=len(a_ids), desc="VGMDB", mininterval=0)

    for a_id in a_ids:
        f = pool.submit(scraper.get_albums, a_id)
        f.add_done_callback(lambda f: not f.exception() and pbar.update(1))
        futures.append(f)

    new_albums = itertools.chain.from_iterable(f.result() for f in futures)
    pool.shutdown()
    pbar.close()
    scraper.__close()

    return new_albums


def _scrape_musicbrainz(urls: list[str], existing_albums: list[Album]) -> list[Album]:
    scraper = MusicBrainzScraper()

    # 获取 release ids
    r_ids = []
    for url in urls:
        if not url.startswith(MusicBrainzScraper.PAGE_ROOT_URL):
            continue
        if "/artist/" in url:
            resp = scraper.lookup_entity(url.split("/artist/")[1].split("/")[0], "artist", "releases+release-groups")
            r_ids.extend([r["id"] for r in resp["releases"]])
            [r_ids.extend(scraper.get_release_ids_from_release_group(rg["id"])) for rg in resp["release-groups"]]

    # 过滤 已存在元数据 的 album ids
    existing_r_ids = [link.split("/")[-1] for a in existing_albums for link in a.links if link.startswith(MusicBrainzScraper.PAGE_ROOT_URL)]
    r_ids = list(set(r_ids) - set(existing_r_ids))

    if not r_ids:
        return []

    # 开始 获取 元数据

    # 检查 PGDATA 路径
    pgdata = Path(g_settings.MUSICBRAINZ_PGDATA)
    if not pgdata.is_dir() or not Path(pgdata, "postgresql.conf").is_file():
        cprint(g_message.OP_20260307_103506.format(pgdata))
        database = None
    else:
        cprint(g_message.OP_20260307_103505.format(pgdata))
        cprint(g_message.OP_20260307_103507)
        pg_ctl_start(pgdata)
        database = MusicBrainzDatabase()

    new_albums = []
    pbar = tqdm(total=len(r_ids), desc="MusicBrainz", mininterval=0)
    for r_id in r_ids:
        try:
            if database:
                albums = database.select_albums(filter_release_id=r_id)
            else:
                albums = scraper.get_album_from_release(r_id)
            new_albums.extend(albums)
        except Exception as e:
            logger.error("", exc_info=1)
            raise e
        
        pbar.update()
    
    pbar.close()

    if database:
        cprint(g_message.OP_20260307_103508)
        pg_ctl_stop(pgdata)

    return new_albums


def _scrape_doujinmusicinfo(urls: list[str], existing_albums: list[Album]) -> list[Album]:
    scraper = DoujinMusicInfoScraper()

    # 获取 cd ids

    cd_ids = []
    for url in urls:
        if not url.startswith(DoujinMusicInfoScraper.ROOT_URL):
            continue
        if "/cd/" in url:
            cd_ids.append(url.split("/cd/")[1].split("/")[0])
        elif "/circle/" in url:
            circle_id = url.split("/")[-1]
            cd_ids.extend(scraper.get_cd_ids_from_circle(circle_id))

    # 过滤 已存在元数据 的 cd ids
    existing_cd_ids = [link.split("/")[-1] for a in existing_albums for link in a.links if link.startswith(DoujinMusicInfoScraper.ROOT_URL)]
    cd_ids = list(set(cd_ids) - set(existing_cd_ids))

    if not cd_ids:
        return []

    # 开始 获取 元数据

    new_albums = []
    pbar = tqdm(total=len(cd_ids), desc="同人音楽info", mininterval=0)
    for a_id in cd_ids:
        try:
            new_albums.append(scraper.get_album_from_cd(a_id))
        except Exception as e:
            logger.error("", exc_info=1)
            raise e
        
        pbar.update()
    
    pbar.close()
    return new_albums


def _scrape_lastfm(urls: list[str], existing_albums: list[Album]) -> list[Album]:
    scraper = LastFMScraper(g_settings.lastfm_api_key)

    # 获取 album ids

    a_ids = []
    for url in urls:
        if not url.startswith(LastFMScraper.PAGE_ROOT_URL):
            continue
        artist, album = (url.strip(LastFMScraper.PAGE_ROOT_URL).strip("/").split("/") + [""])[:2]
        artist, album = artist.strip(), album.strip()
        if album:
            a_ids.append((artist, album))
        else:
            a_ids.extend((artist, n) for n in scraper.get_album_names_from_artist(artist))

    # 过滤 已存在元数据 的 cd ids
    existing_a_ids = [tuple(link.split("/")[-2:]) for a in existing_albums for link in a.links if link.startswith(LastFMScraper.PAGE_ROOT_URL)]
    a_ids = list(set(a_ids) - set(existing_a_ids))

    if not a_ids:
        return []

    # 开始 获取 元数据

    new_albums = []
    pbar = tqdm(total=len(a_ids), desc="Last.FM", mininterval=0)
    for a_id in a_ids:
        try:
            new_albums.append(scraper.get_album(*a_id))
        except Exception as e:
            logger.error("", exc_info=1)
            raise e

        pbar.update()

    pbar.close()
    return new_albums


def scrape_metadata():
    input_urls = easy_cinput(g_message.OP_20260307_103501, return_type=str)
    input_path = easy_cinput(g_message.OP_20260307_103502, 
                             default=Path(g_settings.TMP_DIRECTORY), return_type=Path)

    if input_path.is_file():
        metadata_file = input_path
    else:
        input_path.mkdir(parents=True, exist_ok=True)
        metadata_file = input_path / f"scrape-{datetime.now().strftime("%Y%m%d-%H%M%S")}.toml"

    urls = list(map(str.strip, input_urls.split()))
    existing_albums = load_albums_from_toml(metadata_file) if metadata_file.exists() else []

    scrape_funcs = [_scrape_vgmdb, _scrape_musicbrainz, _scrape_doujinmusicinfo, _scrape_lastfm]
    new_albums = list(itertools.chain.from_iterable(func(urls, existing_albums) for func in scrape_funcs))

    dump_albums_to_toml(existing_albums + new_albums, metadata_file)
    
    cprint(g_message.OP_20260307_103504.format(len(new_albums), metadata_file))




