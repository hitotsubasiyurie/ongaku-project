from datetime import datetime
from pathlib import Path

from tqdm import tqdm

from src.cli.common import easy_linput
from src.core.i18n import MESSAGE
from src.core.logger import logger, lprint
from src.core.settings import settings
from src.core.storage import dump_albums_to_toml, load_albums_from_toml
from src.scraper import VGMdbScraper

OPERATION_NAME = MESSAGE.WF_20251204_194920


def main():
    lprint(MESSAGE.WF_20251204_194921)

    input_path = easy_linput(MESSAGE.WF_20251204_194922.format(settings.temp_directory), 
                             default=Path(settings.temp_directory), return_type=Path)
    input_urls = easy_linput(MESSAGE.WF_20251204_194923, return_type=str)

    # 创建目录
    if input_path.is_file():
        input_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_file = input_path
    else:
        input_path.mkdir(parents=True, exist_ok=True)
        metadata_file = input_path / f"vgmdb-{datetime.now().strftime("%Y%m%d-%H%M%S")}.toml"

    scraper = VGMdbScraper()

    # 获取 album ids

    a_ids = []
    for url in list(map(str.strip, input_urls.split())):
        if "/album/" in url:
            a_ids.append(url.split("/album/")[1].split("/")[0])
        elif "/product/" in url:
            product_id = url.split("/")[-1]
            a_ids.extend(scraper.get_album_ids_from_product(product_id))
        elif "/artist/" in url:
            artist_id = url.split("/")[-1]
            a_ids.extend(scraper.get_album_ids_from_artist(artist_id))
        elif "/search?" in url:
            a_ids.extend(scraper.get_album_ids_from_search_page(url))
        else:
            lprint(MESSAGE.WF_20251204_194924)
            return
    
    exist_albums = load_albums_from_toml(metadata_file) if metadata_file.exists() else []

    # 过滤 已存在元数据 的 album ids
    skip_a_ids = [link.split("/")[-1] for a in exist_albums for link in a.links if link.startswith(VGMdbScraper.ROOT_URL)]
    a_ids = list(set(a_ids) - set(skip_a_ids))

    # 开始 获取 元数据

    new_albums = []
    pbar = tqdm(total=len(a_ids), mininterval=0)
    for a_id in a_ids:
        try:
            new_albums.extend(scraper.get_albums(a_id))
        except Exception as e:
            logger.error("", exc_info=1)
            raise e
        
        pbar.update()
    
    pbar.close()
    
    dump_albums_to_toml(exist_albums + new_albums, metadata_file)
    
    lprint(MESSAGE.WF_20251204_194925.format(len(new_albums), metadata_file))



