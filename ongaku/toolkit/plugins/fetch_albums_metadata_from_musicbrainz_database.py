import subprocess
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from tqdm import tqdm

from ongaku.core.logger import logger, lprint
from ongaku.core.settings import global_settings
from ongaku.core.kanban import dump_albums_to_toml, load_albums_from_toml
from ongaku.toolkit.toolkit_utils import easy_linput
from ongaku.utils.basemodel_utils import abstract_tracks_info
from ongaku.crawlers.musicbrainz_database import MusicBrainzDatabase, pg_ctl_start, pg_ctl_stop


if global_settings.language == "zh":
    PLUGIN_NAME = "从本地 MusicBrainz 数据库获取专辑元数据"
elif global_settings.language == "ja":
    pass
else:
    pass


MESSAGE = SimpleNamespace()


if global_settings.language == "zh":
    MESSAGE.C3X = \
"""
给定一个元数据文件，从本地 MusicBrainz 数据库中查询对应的专辑。
"""
    MESSAGE.SER = "本地 MusicBrainz 数据库 PGDATA 路径为空。{}"
    MESSAGE.OG9 = "请输入待查询的元数据文件："
    MESSAGE.K98 = "请输入筛选掩码列表 [catalognumber, date, date_int, track_count]（默认为 1000,0101）："
    MESSAGE.ERT = "请输入排序掩码 [catalognumber, album, tracks_abstract]（默认为 111）："
    MESSAGE.D96 = "请输入每张专辑查询结果数限制（默认为 10）："
    MESSAGE.FGT = "正在启动 MusicBrainz 数据库..."
    MESSAGE.WE7 = "成功获取 {:d} 张专辑元数据。元数据文件：{}"
    MESSAGE.GH5 = "正在关闭 MusicBrainz 数据库..."
elif global_settings.language == "ja":
    pass
else:
    pass


def main():

    # 检查 PGDATA 路径
    pgdata = Path(global_settings.temp_directory, "musicbrainz_pgdata")
    if not pgdata.is_dir() or not Path(pgdata, "postgresql.conf").is_file():
        lprint(MESSAGE.SER.format(pgdata))
        return
    
    metadata_file = easy_linput(MESSAGE.OG9, return_type=Path)
    filter_masks = easy_linput(MESSAGE.K98, default="1000, 0101", return_type=str)
    order_mask = easy_linput(MESSAGE.ERT, default="111", return_type=str)
    limit = easy_linput(MESSAGE.D96, default=10, return_type=int)

    result_file = metadata_file.parent / f"Fetch-{datetime.now().strftime("%Y%m%d_%H%M%S")}.toml"

    lprint(MESSAGE.FGT)
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

    lprint(MESSAGE.WE7.format(len(result_albums), result_file))

    lprint(MESSAGE.GH5)
    pg_ctl_stop(pgdata)

    subprocess.run(f'explorer /select,"{result_file}"')
