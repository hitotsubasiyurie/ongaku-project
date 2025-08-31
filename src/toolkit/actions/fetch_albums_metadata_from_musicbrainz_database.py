from datetime import datetime
from pathlib import Path

from tqdm import tqdm

from src.logger import logger, lprint
from src.toolkit.message import MESSAGE
from src.toolkit.toolkit_utils import easy_linput
from src.basemodel_utils import abstract_tracks_info
from src.toolkit.metadata_source.musicbrainz_database import MusicBrainzDatabase
from src.repository.ongaku_repository import dump_albums_to_toml, load_albums_from_toml


def fetch_albums_metadata_from_musicbrainz_database():

    metadata_file: Path = easy_linput(MESSAGE.LLZ4XB9J, return_type=Path)
    filter_masks: str = easy_linput(MESSAGE.M82LXNFV, default="1000, 0101", return_type=str)
    limit: int = easy_linput(MESSAGE.ZG85TEHZ, default=10, return_type=int)
    order_mask: str = easy_linput(MESSAGE.CCKZUKK1, default="111", return_type=str)

    result_file = metadata_file.parent / f'"Fetch-{datetime.now().strftime("%Y%m%d_%H%M%S")}.toml"'

    database = MusicBrainzDatabase()

    # 跳过 已有 musicbrainz link 的专辑
    to_query_albums = [a for a in load_albums_from_toml(metadata_file) 
              if all("musicbrainz" not in l for l in a.links)]
    
    result_albums = []

    pbar = tqdm(total=len(to_query_albums), mininterval=0)
    for album in to_query_albums:

        filter_params = [album.catalognumber, album.date, 
                         sum(MusicBrainzDatabase._date_str_to_range(album.date))//2, len(album.tracks)]
        order_params = [album.catalognumber, album.album, abstract_tracks_info(album)]

        args2 = [x if int(b) else None for b, x in zip(order_mask, order_params)]

        for filter_mask in map(str.strip, filter_masks.split(",")):
            args1 = [x if int(b) else None for b, x in zip(filter_mask, filter_params)]

            # 允许 全表扫描
            result_albums.extend(database.select_albums(None, *args1, *args2, limit=limit, allow_full_scan=True))

        pbar.update()

    # 关闭 进度条
    pbar.close()

    # 去重
    result_albums = list(set(result_albums))
    
    dump_albums_to_toml(result_albums, result_file)

    lprint(MESSAGE.ZX1XSCFX.format(len(result_albums), result_file))
