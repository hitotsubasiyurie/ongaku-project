from datetime import datetime
from pathlib import Path

from tqdm import tqdm

from src.core.kanban import dump_albums_to_toml, load_albums_from_toml
from src.core.logger import logger, lprint
from src.core.settings import global_settings
from src.lang import MESSAGE
from src.scraper.dojin_music_info_api import DoujinMusicInfoAPI
from src.workflow.common import easy_linput

OPERATION_NAME = MESSAGE.WF_20251204_194820


# 主函数

def main():
    lprint(MESSAGE.WF_20251204_194821)

    input_path = easy_linput(MESSAGE.WF_20251204_194822, return_type=Path)
    input_urls = easy_linput(MESSAGE.WF_20251204_194823, return_type=str)

    # 创建目录
    if input_path.is_file():
        input_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_file = input_path
    else:
        input_path.mkdir(parents=True, exist_ok=True)
        metadata_file = input_path / f"Fetch-{datetime.now().strftime("%Y%m%d_%H%M%S")}.toml"

    cache_dir = Path(global_settings.temp_directory, "cache")
    cache_dir.mkdir(parents=True, exist_ok=True)

    api = DoujinMusicInfoAPI(cache_dir=cache_dir)

    # 获取 cd ids

    cd_ids = []
    for url in list(map(str.strip, input_urls.split())):
        if "/cd/" in url:
            cd_ids.append(url.split("/cd/")[1].split("/")[0])
        elif "/circle/" in url:
            circle_id = url.split("/")[-1]
            cd_ids.extend(api.get_cd_ids_from_circle(circle_id))
        else:
            lprint(MESSAGE.WF_20251204_194824)
            return
    
    exist_albums = load_albums_from_toml(metadata_file) if metadata_file.exists() else []

    # 过滤 已存在元数据 的 album ids
    skip_a_ids = [link.split("/")[-1] for a in exist_albums for link in a.links if link.startswith(DoujinMusicInfoAPI.ROOT_URL)]
    cd_ids = list(set(cd_ids) - set(skip_a_ids))

    # 开始 获取 元数据

    new_albums = []
    pbar = tqdm(total=len(cd_ids), mininterval=0)
    for a_id in cd_ids:
        try:
            new_albums.append(api.get_album_from_cd(a_id))
        except Exception as e:
            logger.error("", exc_info=1)
            raise e
        
        pbar.update()
    
    pbar.close()
    
    dump_albums_to_toml(exist_albums + new_albums, metadata_file)
    
    lprint(MESSAGE.WF_20251204_194825.format(len(new_albums), metadata_file))
