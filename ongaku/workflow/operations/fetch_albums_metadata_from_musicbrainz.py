from pathlib import Path
from datetime import datetime

from tqdm import tqdm

from ongaku.core.logger import logger, lprint
from ongaku.core.settings import global_settings
from ongaku.workflow.common import easy_linput
from ongaku.mdsource.musicbrainz_api import MusicBrainzAPI
from ongaku.core.kanban import dump_albums_to_toml, load_albums_from_toml
from ongaku.mdsource.musicbrainz_database import MusicBrainzDatabase, pg_ctl_start, pg_ctl_stop


if global_settings.language == "zh":
    OPERATION_NAME = "从 MusicBrainz 获取专辑元数据"
    class MESSAGE:
        OLI4J5 = """
保存路径：
    若是文件夹，将会在其下生成新的元数据文件。
    若是已有的元数据文件路径，将会追加它未包含的专辑元数据

MusicBrainz url ：
    artist 页面，例如：https://beta.musicbrainz.org/artist/f960979c-fc79-4cef-8cf5-fda334e11445
    如果有多个 url ，请使用空格分隔，例如：url1 url2 url3
    """
        SOPOPL = "请输入保存路径："
        GFD8P9 = "请输入 MusicBrainz url ："
        RE5LKM = "不支持的 MusicBrainz url 。"
        SOPLP0 = "本地 MusicBrainz 数据库 PGDATA 路径不存在。{}"
        DRPPP0 = "本地 MusicBrainz 数据库 PGDATA 路径存在。{}"
        IOP596 = "成功获取 {:d} 张专辑元数据。元数据文件：{}"
        DFFBHJ = "正在启动 MusicBrainz 数据库..."
        MKLP9O = "正在关闭 MusicBrainz 数据库..."
elif global_settings.language == "ja":
    pass
else:
    pass


################ 主函数 ################

def main():
    lprint(MESSAGE.OLI4J5)

    input_path = easy_linput(MESSAGE.SOPOPL, return_type=Path)
    input_urls = easy_linput(MESSAGE.GFD8P9, return_type=str)

    # 创建目录
    if input_path.is_file():
        input_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_file = input_path
    else:
        input_path.mkdir(parents=True, exist_ok=True)
        metadata_file = input_path / f"Fetch-{datetime.now().strftime("%Y%m%d_%H%M%S")}.toml"

    cache_dir = Path(global_settings.temp_directory, "cache")
    cache_dir.mkdir(parents=True, exist_ok=True)

    api = MusicBrainzAPI(cache_dir=cache_dir)

    # 获取 release ids
    r_ids = []
    for url in list(map(str.strip, input_urls.split())):
        if "/artist/" in url:
            resp = api.lookup_entity(url.split("/artist/")[1].split("/")[0], "artist", "releases+release-groups")
            r_ids.extend([r["id"] for r in resp["releases"]])
            [r_ids.extend(api.get_album_ids_from_release_group(rg["id"])) for rg in resp["release-groups"]]
        else:
            lprint(MESSAGE.RE5LKM)
            return
    
    exist_albums = load_albums_from_toml(metadata_file) if metadata_file.exists() else []

    # 过滤 已存在元数据 的 album ids
    skip_r_ids = [link.split("/")[-1] for a in exist_albums for link in a.links if link.startswith(MusicBrainzAPI.RELEASE_PAGE_URL)]
    r_ids = list(set(r_ids) - set(skip_r_ids))

    # 开始 获取 元数据

    # 检查 PGDATA 路径
    pgdata = Path(global_settings.temp_directory, "musicbrainz_pgdata")
    if not pgdata.is_dir() or not Path(pgdata, "postgresql.conf").is_file():
        lprint(MESSAGE.SOPLP0.format(pgdata))
        database = None
    else:
        lprint(MESSAGE.DRPPP0.format(pgdata))
        lprint(MESSAGE.DFFBHJ)
        pg_ctl_start(pgdata)
        database = MusicBrainzDatabase()

    new_albums = []
    pbar = tqdm(total=len(r_ids), mininterval=0)
    for r_id in r_ids:
        try:
            if database:
                albums = database.select_albums(filter_release_id=r_id)
            else:
                albums = api.get_album_from_release(r_id)
            new_albums.extend(albums)
        except Exception as e:
            logger.error("", exc_info=1)
            raise e
        
        pbar.update()
    
    pbar.close()
    
    dump_albums_to_toml(exist_albums + new_albums, metadata_file)
    
    lprint(MESSAGE.IOP596.format(len(new_albums), metadata_file))

    if database:
        lprint(MESSAGE.MKLP9O)
        pg_ctl_stop(pgdata)



