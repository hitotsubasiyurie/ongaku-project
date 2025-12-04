from datetime import datetime
from pathlib import Path

from tqdm import tqdm

from ongaku.core.logger import logger, lprint
from ongaku.core.settings import global_settings
from ongaku.core.kanban import dump_albums_to_toml, load_albums_from_toml
from ongaku.lang import MESSAGE
from ongaku.workflow.common import easy_linput
from ongaku.workflow.common import abstract_tracks_info
from ongaku.mdsource.musicbrainz_database import MusicBrainzDatabase, pg_ctl_start, pg_ctl_stop


OPERATION_NAME = MESSAGE.WF_20251204_195520


######## 主函数 ########

def main():
    lprint(MESSAGE.WF_20251204_195521)

    # 检查 PGDATA 路径
    pgdata = Path(global_settings.temp_directory, "musicbrainz_pgdata")
    if not pgdata.is_dir() or not Path(pgdata, "postgresql.conf").is_file():
        lprint(MESSAGE.WF_20251204_195522.format(pgdata))
        return
    lprint(MESSAGE.WF_20251204_195523.format(pgdata))
    
    metadata_file = easy_linput(MESSAGE.WF_20251204_195524, return_type=Path)
    filter_masks = easy_linput(MESSAGE.WF_20251204_195525, default="1000, 0101", return_type=str)
    order_mask = easy_linput(MESSAGE.WF_20251204_195526, default="111", return_type=str)
    limit = easy_linput(MESSAGE.WF_20251204_195527, default=10, return_type=int)

    result_file = metadata_file.parent / f"Fetch-{datetime.now().strftime("%Y%m%d_%H%M%S")}.toml"

    lprint(MESSAGE.WF_20251204_195528)
    pg_ctl_start(pgdata)

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

            # 不允许 全表扫描
            result_albums.extend(database.select_albums(None, *args1, *args2, limit=limit, allow_full_scan=False))

        pbar.update()

    # 关闭 进度条
    pbar.close()

    # 去重
    result_albums = list(set(result_albums))
    
    dump_albums_to_toml(result_albums, result_file)

    lprint(MESSAGE.WF_20251204_195529.format(len(result_albums), result_file))

    lprint(MESSAGE.WF_20251204_195530)
    pg_ctl_stop(pgdata)




