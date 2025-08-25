import os
import re
import sys
import itertools
import tomllib
from datetime import datetime
from pathlib import Path
from collections import defaultdict

import orjson
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.logger import logger, _ongaku_logger
from src.common.ongaku_exception import OngakuException
from src.metadata_source.vgmdb_api import VGMdbAPI
from src.repository.ongaku_repository import dump_albums_to_toml, load_albums_from_toml


if __name__ == "__main__":

    # input 输入
    
    metadata_dir = input(f"Please input metadata directory: ").strip("'\"")
    theme = input(f"Please input theme: ").strip()
    cache_dir = input(f"Please input cache directory: ").strip("'\"")

    if not metadata_dir or not theme or not cache_dir:
        sys.exit(0)
    
    metadata_dir, cache_dir = Path(metadata_dir), Path(cache_dir)

    # 创建目录
    metadata_dir.parent.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    theme_file = Path(metadata_dir, theme + ".toml")
    theme_pending_file = Path(metadata_dir, theme + ".pending" + ".toml")
    
    input_url = input("Please input VGMDB page url (frachise page, product page, search page): ")

    # 日志输出至文件
    if not _ongaku_logger.outfile:
        _ongaku_logger.set_outfile(metadata_dir / f"{datetime.now().strftime("%Y-%d-%m-%H-%M-%S")}.log")

    api = VGMdbAPI(cache_dir=cache_dir)

    # 获取 album ids

    if "/product/" in input_url:
        product_id = input_url.split("/")[-1]
        a_ids = api.get_album_ids_from_product(product_id)
    elif "/search?" in input_url:
        a_ids = api.get_album_ids_from_search_page(input_url)
    else:
        logger.error(f"Not supported url. {input_url}")
        raise OngakuException()
    
    # 跳过 已存在元数据 的 album ids

    skip_a_ids = []

    for file in [theme_file, theme_pending_file]:
        if not file.exists():
            continue
        skip_a_ids.extend(link.split("/")[-1] for a in load_albums_from_toml(file) 
                          for link in a.links if link.startswith(VGMdbAPI.ROOT_URL))

    a_ids = list(set(a_ids) - set(skip_a_ids))

    logger.info(f"Got {len(a_ids)} album ids to be fetched.")
    logger.debug(a_ids)

    # 开始 获取 元数据

    pbar = tqdm(total=len(a_ids), mininterval=0)
    fetched_albums = []
    for a_id in a_ids:
        try:
            fetched_albums.extend(api.get_albums(a_id))
        except Exception as e:
            logger.error("", exc_info=1)
            raise e
        
        pbar.update()

    # 追加进 pending file
    
    if theme_pending_file.exists():
        albums = load_albums_from_toml(theme_pending_file) + fetched_albums
    else:
        albums = fetched_albums

    dump_albums_to_toml(albums, theme_pending_file)

