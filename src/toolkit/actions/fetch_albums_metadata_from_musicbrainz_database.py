import sys
import time
from pathlib import Path

from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.logger import logger, _ongaku_logger
from src.basemodel_utils import abstract_tracks_info
from src.metadata_source.musicbrainz_database import MusicBrainzDatabase
from src.repository.ongaku_repository import dump_albums_to_toml, load_albums_from_toml


if __name__ == "__main__":

    # input 输入

    metadata_file = input(f"Please input a metadata file to query: ").strip("'\"")
    filter_masks = input("Please input filter masks [catalognumber, date, date_int, track_count] (default 1101, 1100, 1001, 1000): ") or "1101, 1100, 1001, 1000"
    limit = int(input("Please input query result limit (default 10): ").strip() or 10)
    order_mask = input("Please input similarity order mask [catalognumber, album, tracks_abstract] (default 000): ").strip() or "000"

    if not metadata_file:
        sys.exit(0)

    metadata_file = Path(metadata_file)

    result_file = metadata_file.parent / f"Fetch-{int(time.time())}.toml"

    # 日志输出至目录
    if not _ongaku_logger.outfile:
        _ongaku_logger.set_outfile(metadata_file.parent)

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

    print(f"Fetched successfully. {result_file}")
