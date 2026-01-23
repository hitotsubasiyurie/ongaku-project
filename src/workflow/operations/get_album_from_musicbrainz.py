from datetime import datetime
from pathlib import Path

from tqdm import tqdm

from src.core.kanban import dump_albums_to_toml, load_albums_from_toml
from src.core.logger import logger, lprint
from src.core.settings import global_settings
from src.lang import MESSAGE
from src.scraper import MusicBrainzScraper
from src.scraper.musicbrainz_database import MusicBrainzDatabase, pg_ctl_start, pg_ctl_stop
from src.workflow.common import easy_linput


OPERATION_NAME = MESSAGE.WF_20251204_195320


# 主函数

def main():
    lprint(MESSAGE.WF_20251204_195321)

    input_path = easy_linput(MESSAGE.WF_20251204_195322.format(global_settings.temp_directory), 
                             default=Path(global_settings.temp_directory), return_type=Path)
    input_urls = easy_linput(MESSAGE.WF_20251204_195323, return_type=str)

    # 创建目录
    if input_path.is_file():
        input_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_file = input_path
    else:
        input_path.mkdir(parents=True, exist_ok=True)
        metadata_file = input_path / f"musicbrainz-{datetime.now().strftime("%Y%m%d-%H%M%S")}.toml"

    scraper = MusicBrainzScraper()

    # 获取 release ids
    r_ids = []
    for url in list(map(str.strip, input_urls.split())):
        if "/artist/" in url:
            resp = scraper.lookup_entity(url.split("/artist/")[1].split("/")[0], "artist", "releases+release-groups")
            r_ids.extend([r["id"] for r in resp["releases"]])
            [r_ids.extend(scraper.get_album_ids_from_release_group(rg["id"])) for rg in resp["release-groups"]]
        else:
            lprint(MESSAGE.WF_20251204_195324)
            return
    
    exist_albums = load_albums_from_toml(metadata_file) if metadata_file.exists() else []

    # 过滤 已存在元数据 的 album ids
    skip_r_ids = [link.split("/")[-1] for a in exist_albums for link in a.links if link.startswith(MusicBrainzScraper.RELEASE_PAGE_URL)]
    r_ids = list(set(r_ids) - set(skip_r_ids))

    # 开始 获取 元数据

    # 检查 PGDATA 路径
    pgdata = Path(global_settings.temp_directory, "musicbrainz_pgdata")
    if not pgdata.is_dir() or not Path(pgdata, "postgresql.conf").is_file():
        lprint(MESSAGE.WF_20251204_195325.format(pgdata))
        database = None
    else:
        lprint(MESSAGE.WF_20251204_195326.format(pgdata))
        lprint(MESSAGE.WF_20251204_195328)
        pg_ctl_start(pgdata)
        database = MusicBrainzDatabase()

    new_albums = []
    pbar = tqdm(total=len(r_ids), mininterval=0)
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
    
    dump_albums_to_toml(exist_albums + new_albums, metadata_file)
    
    lprint(MESSAGE.WF_20251204_195327.format(len(new_albums), metadata_file))

    if database:
        lprint(MESSAGE.WF_20251204_195329)
        pg_ctl_stop(pgdata)



