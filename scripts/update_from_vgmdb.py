import os
import re
import sys
import itertools
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.logger import logger
from src.common.constants import METADATA_PATH, TMP_PATH
from src.common.utils import strings_assignment
from src.common.exception import OngakuException
from src.metadata_source.vgmdb_api import VGMdbAPI
from src.ongaku_library.ongaku_library import dump_album_model, album_filename, OngakuScanner


if __name__ == "__main__":

    # input 输入

    save_dir = input(f"Please input save directory ({METADATA_PATH}): ").strip("'\"") or METADATA_PATH
    cache_dir = os.path.join(TMP_PATH, "cache") if TMP_PATH else ""
    cache_dir = input(f"Please input cache directory ({cache_dir}): ").strip("'\"") or cache_dir

    if not save_dir or not cache_dir:
        sys.exit(0)
    
    save_dir, cache_dir = Path(save_dir), Path(cache_dir)
    
    input_url = input("Please input VGMDB page (frachise page, product page, search page): ")

    save_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    # 获取 themes_dict album_ids

    api = VGMdbAPI(cache_dir=cache_dir)

    themes_dict = defaultdict(list)

    if "/product/" in input_url:
        given_pid = input_url.split("/")[-1]

        p_ids: list[str] = [given_pid] + api.get_product_ids_from_franchise(given_pid)

        p_titles_s: list[list[str]] = [api.get_product_titles(p_id) for p_id in p_ids]
        a_ids_s: list[list[str]] = [api.get_album_ids_from_product(p_id) for p_id in p_ids]

        for p_titles, a_ids in zip(p_titles_s, a_ids_s):
            [themes_dict[a_id].extend(p_titles) for a_id in a_ids]

        a_ids = set(itertools.chain.from_iterable(a_ids_s))

    elif "/search?" in input_url:
        a_ids = set(api.get_album_ids_from_page(input_url))
    
    else:
        logger.error(f"Not supported url. {input_url}")
        raise OngakuException()
    
    # 跳过已有元数据文件的 album_ids

    skip_a_ids = set()
    for f in OngakuScanner._scan_metadata_files(save_dir):
        match = re.search(VGMdbAPI.ALBUM_URL_PATTERN, Path(f).read_text(encoding="utf-8"))
        if match:
            skip_a_ids.add(match.group(1))

    a_ids -= skip_a_ids

    logger.info(f"Got {len(a_ids)} album ids to be updated.")
    logger.debug(a_ids)

    # 开始更新

    for a_id in a_ids:
        try:
            # 获取 album
            albums = api.get_albums(a_id)
            # 填充 theme 信息 排序
            for a in albums:
                a.themes = list(sorted(set(themes_dict[a_id])))
        # 遇到异常 记录日志 直接退出
        except Exception as e:
            logger.error("", exc_info=1)
            raise e
        
        [dump_album_model(a, save_dir / (album_filename(a)+".json")) for a in albums]


