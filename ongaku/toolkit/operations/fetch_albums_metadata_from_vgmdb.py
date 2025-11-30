from pathlib import Path
from datetime import datetime
from types import SimpleNamespace

from tqdm import tqdm

from ongaku.core.logger import logger, lprint
from ongaku.core.settings import global_settings
from ongaku.toolkit.utils import easy_linput
from ongaku.mdsource.vgmdb_api import VGMdbAPI
from ongaku.core.kanban import dump_albums_to_toml, load_albums_from_toml


if global_settings.language == "zh":
    PLUGIN_NAME = "从 VGMDB 获取专辑元数据"
elif global_settings.language == "ja":
    pass
else:
    pass


MESSAGE = SimpleNamespace()


if global_settings.language == "zh":
    MESSAGE.C3X = \
"""
保存路径：
    若是文件夹，将会在其下生成新的元数据文件。
    若是已有的元数据文件路径，将会追加它未包含的专辑元数据

VGMDB url ：
    album 页面，例如：https://vgmdb.net/album/27425
    frachise 页面，例如：https://vgmdb.net/product/3559
    product 页面，例如：https://vgmdb.net/product/7750
    搜索页面，例如：https://vgmdb.net/search?q=Yosuga+no+Sora&type=
    如果有多个 url ，请使用空格分隔，例如：https://vgmdb.net/product/3559 https://vgmdb.net/product/7750 https://vgmdb.net/search?q=Yosuga+no+Sora&type=
"""
    MESSAGE.OG9 = "请输入保存路径："
    MESSAGE.K98 = "请输入 VGMDB url ："
    MESSAGE.D96 = "不支持的 VGMDB url 。"
    MESSAGE.ERT = "成功获取 {:d} 张专辑元数据。元数据文件：{}"
elif global_settings.language == "ja":
    pass
else:
    pass


def main():
    lprint(MESSAGE.C3X)

    input_path = easy_linput(MESSAGE.OG9, return_type=Path)
    input_urls = easy_linput(MESSAGE.K98, return_type=str)

    # 创建目录
    if input_path.is_file():
        input_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_file = input_path
    else:
        input_path.mkdir(parents=True, exist_ok=True)
        metadata_file = input_path / f"Fetch-{datetime.now().strftime("%Y%m%d_%H%M%S")}.toml"

    cache_dir = Path(global_settings.temp_directory, "cache")
    cache_dir.mkdir(parents=True, exist_ok=True)

    api = VGMdbAPI(cache_dir=cache_dir)

    # 获取 album ids

    a_ids = []
    for url in list(map(str.strip, input_urls.split())):
        if "/album/" in url:
            a_ids.append(url.split("/album/")[1].split("/")[0])
        elif "/product/" in url:
            product_id = url.split("/")[-1]
            a_ids.extend(api.get_album_ids_from_product(product_id))
        elif "/search?" in url:
            a_ids.extend(api.get_album_ids_from_search_page(url))
        else:
            lprint(MESSAGE.D96)
            return
    
    exist_albums = load_albums_from_toml(metadata_file) if metadata_file.exists() else []

    # 过滤 已存在元数据 的 album ids
    skip_a_ids = [link.split("/")[-1] for a in exist_albums for link in a.links if link.startswith(VGMdbAPI.ROOT_URL)]
    a_ids = list(set(a_ids) - set(skip_a_ids))

    # 开始 获取 元数据

    new_albums = []
    pbar = tqdm(total=len(a_ids), mininterval=0)
    for a_id in a_ids:
        try:
            new_albums.extend(api.get_albums(a_id))
        except Exception as e:
            logger.error("", exc_info=1)
            raise e
        
        pbar.update()
    
    pbar.close()
    
    dump_albums_to_toml(exist_albums + new_albums, metadata_file)
    
    lprint(MESSAGE.ERT.format(len(new_albums), metadata_file))
