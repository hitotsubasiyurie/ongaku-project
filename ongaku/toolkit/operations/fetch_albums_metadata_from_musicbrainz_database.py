from datetime import datetime
from pathlib import Path

from tqdm import tqdm

from ongaku.core.logger import logger, lprint
from ongaku.core.settings import global_settings
from ongaku.core.kanban import dump_albums_to_toml, load_albums_from_toml
from ongaku.toolkit.utils import easy_linput
from ongaku.utils.basemodel_utils import abstract_tracks_info
from ongaku.mdsource.musicbrainz_database import MusicBrainzDatabase, pg_ctl_start, pg_ctl_stop


if global_settings.language == "zh":
    PLUGIN_NAME = "从本地 MusicBrainz 数据库获取专辑元数据"
    class MESSAGE:
        OLI4J5 = """
给定一个元数据文件，从本地 MusicBrainz 数据库中查询对应的专辑。
    """
        SOPLP0 = "本地 MusicBrainz 数据库 PGDATA 路径不存在。{}"
        DRPPP0 = "本地 MusicBrainz 数据库 PGDATA 路径存在。{}"
        GFD8P9 = "请输入待查询的元数据文件："
        RE5LKM = "请输入筛选掩码列表 [catalognumber, date, date_int, track_count]（默认为 1000,0101）："
        IOP596 = "请输入排序掩码 [catalognumber, album, tracks_abstract]（默认为 111）："
        OKI890 = "请输入每张专辑查询结果数限制（默认为 10）："
        DFFBHJ = "正在启动 MusicBrainz 数据库..."
        DVG877 = "成功获取 {:d} 张专辑元数据。元数据文件：{}"
        MKLP9O = "正在关闭 MusicBrainz 数据库..."
elif global_settings.language == "ja":
    pass
else:
    pass


################ 主函数 ################

def main():
    lprint(MESSAGE.OLI4J5)

    # 检查 PGDATA 路径
    pgdata = Path(global_settings.temp_directory, "musicbrainz_pgdata")
    if not pgdata.is_dir() or not Path(pgdata, "postgresql.conf").is_file():
        lprint(MESSAGE.SOPLP0.format(pgdata))
        return
    lprint(MESSAGE.DRPPP0.format(pgdata))
    
    metadata_file = easy_linput(MESSAGE.GFD8P9, return_type=Path)
    filter_masks = easy_linput(MESSAGE.RE5LKM, default="1000, 0101", return_type=str)
    order_mask = easy_linput(MESSAGE.IOP596, default="111", return_type=str)
    limit = easy_linput(MESSAGE.OKI890, default=10, return_type=int)

    result_file = metadata_file.parent / f"Fetch-{datetime.now().strftime("%Y%m%d_%H%M%S")}.toml"

    lprint(MESSAGE.DFFBHJ)
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

    lprint(MESSAGE.DVG877.format(len(result_albums), result_file))

    lprint(MESSAGE.MKLP9O)
    pg_ctl_stop(pgdata)




