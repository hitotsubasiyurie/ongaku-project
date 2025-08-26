import sys
import time
from pathlib import Path

from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.logger import logger, _ongaku_logger
from src.common.ongaku_exception import OngakuException
from src.metadata_source.vgmdb_api import VGMdbAPI
from src.repository.ongaku_repository import dump_albums_to_toml, load_albums_from_toml


if __name__ == "__main__":

    # input 输入
    
    input_path = input(f"Please input a directory to save or a metadata file to append: ").strip("'\"")
    cache_dir = input(f"Please input cache directory: ").strip("'\"")

    if not all([input_path, cache_dir]):
        sys.exit(0)
    
    input_path, cache_dir = Path(input_path), Path(cache_dir)

    if input_path.is_file():
        metadata_file = input_path
    else:
        input_path.mkdir(parents=True, exist_ok=True)
        metadata_file = input_path / f"Fetch-{int(time.time())}.toml"

    # 创建目录
    cache_dir.mkdir(parents=True, exist_ok=True)

    input_url = input("Please input VGMDB page url (frachise page, product page, search page): ")

    # 日志输出至文件
    if not _ongaku_logger.outfile:
        _ongaku_logger.set_outfile(metadata_file.parent)

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

    print(f"Fetched successfully. {metadata_file}")

