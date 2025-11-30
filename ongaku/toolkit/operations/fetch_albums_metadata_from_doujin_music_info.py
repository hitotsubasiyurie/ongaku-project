from pathlib import Path
from datetime import datetime
from types import SimpleNamespace

from tqdm import tqdm

from ongaku.core.logger import logger, lprint
from ongaku.core.settings import global_settings
from ongaku.toolkit.utils import easy_linput
from ongaku.mdsource.dojin_music_info_api import DoujinMusicInfoAPI
from ongaku.core.kanban import dump_albums_to_toml, load_albums_from_toml


if global_settings.language == "zh":
    PLUGIN_NAME = "从 同人音楽info 获取专辑元数据"
    class MESSAGE:
        C3XYH9 = \
"""
保存路径：
    若是文件夹，将会在其下生成新的元数据文件。
    若是已有的元数据文件路径，将会追加它未包含的专辑元数据

同人音楽info url ：
    circle 页面，例如：https://www.dojin-music.info/circle/115
    cd 页面，例如：https://www.dojin-music.info/cd/458
    如果有多个 url ，请使用空格分隔，例如：
"""
        OG9DF4 = "请输入保存路径："
        K98BVF = "请输入 同人音楽info url ："
        D96HN3 = "不支持的 同人音楽info url 。"
        EREE5T = "成功获取 {:d} 张专辑元数据。元数据文件：{}"
elif global_settings.language == "ja":
    pass
else:
    pass


################ 主函数 ################

def main():
    lprint(MESSAGE.C3XYH9)

    input_path = easy_linput(MESSAGE.OG9DF4, return_type=Path)
    input_urls = easy_linput(MESSAGE.K98BVF, return_type=str)

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
            lprint(MESSAGE.D96HN3)
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
    
    lprint(MESSAGE.EREE5T.format(len(new_albums), metadata_file))
