from pathlib import Path
from datetime import datetime

from tqdm import tqdm

from src.logger import logger, lprint
from src.global_settings import global_settings
from src.toolkit.message import MESSAGE
from src.toolkit.toolkit_utils import easy_linput
from src.ongaku_exception import OngakuException
from src.toolkit.metadata_source.vgmdb_api import VGMdbAPI
from src.repository.ongaku_repository import dump_albums_to_toml, load_albums_from_toml


def fetch_albums_metadata_from_vgmdb():

    lprint(MESSAGE.K9FYO55X)

    input_path: Path = easy_linput(MESSAGE.YHEH6TFR, return_type=Path)
    input_url: str = easy_linput(MESSAGE.UZKMVOC1, return_type=str)

    # 创建目录
    if input_path.is_file():
        metadata_file = input_path
    else:
        input_path.mkdir(parents=True, exist_ok=True)
        metadata_file = input_path / f'"Fetch-{datetime.now().strftime("%Y%m%d_%H%M%S")}.toml"'

    if global_settings.temp_directory:
        cache_dir = Path(global_settings.temp_directory, "cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
    else:
        cache_dir = None

    api = VGMdbAPI(cache_dir=cache_dir)

    # 获取 album ids

    if "/product/" in input_url:
        product_id = input_url.split("/")[-1]
        a_ids = api.get_album_ids_from_product(product_id)
    elif "/search?" in input_url:
        a_ids = api.get_album_ids_from_search_page(input_url)
    else:
        lprint(MESSAGE.O9W853SZ)
        return
    
    albums = load_albums_from_toml(metadata_file) if metadata_file.exists() else []

    # 跳过 已存在元数据 的 album ids
    skip_a_ids = [link.split("/")[-1] for a in albums for link in a.links if link.startswith(VGMdbAPI.ROOT_URL)]
    a_ids = list(set(a_ids) - set(skip_a_ids))

    # 开始 获取 元数据

    pbar = tqdm(total=len(a_ids), mininterval=0)
    for a_id in a_ids:
        try:
            albums.extend(api.get_albums(a_id))
        except Exception as e:
            logger.error("", exc_info=1)
            raise e
        
        pbar.update()

    dump_albums_to_toml(albums, metadata_file)
    
    pbar.close()
    lprint(MESSAGE.W5OJ7854.format(len(albums), metadata_file))
