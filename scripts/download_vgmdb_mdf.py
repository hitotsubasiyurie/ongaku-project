import sys
import itertools
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.logger import logger
from src.common.constants import TMP_PATH
from src.common.exception import OngakuException
from src.metadata_source.vgmdb_api import VGMdbAPI
from src.ongaku_library.mdf_util import save_album, album_filename


if __name__ == "__main__":

    dst_dir = Path(input("Input save dir (will makedirs): ").strip("'\""))
    cache_dir = Path(input(f"Input cache dir (will makedirs): ").strip("'\""))
    given_url = input("Input VGMDB page (frachise page, product page, search page): ")

    dst_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    api = VGMdbAPI(cache_dir=cache_dir)

    themes_dict = defaultdict(list)

    if "/product/" in given_url:
        given_pid = given_url.split("/")[-1]

        p_ids: list[str] = [given_pid] + api.get_product_ids_from_franchise(given_pid)

        p_titles_s: list[list[str]] = [api.get_product_titles(p_id) for p_id in p_ids]
        a_ids_s: list[list[str]] = [api.get_album_ids_from_product(p_id) for p_id in p_ids]

        for p_titles, a_ids in zip(p_titles_s, a_ids_s):
            [themes_dict[a_id].extend(p_titles) for a_id in a_ids]

        a_ids = set(itertools.chain.from_iterable(a_ids_s))

    elif "/search?" in given_url:
        a_ids = api.get_album_ids_from_page(given_url)
    
    else:
        logger.error(f"Not supported url. {given_url}")
        raise OngakuException()

    for a_id in a_ids:
        url = api.ALBUM_URL_FMT.format(a_id)

        try:
            albums = api.get_albums(a_id)
        except Exception as e:
            logger.error("", exc_info=1)
            raise e
        
        for album in albums:
            album.themes = list(set(themes_dict[a_id]))
            save_album(album, dst_dir / (album_filename(album)+".json"))

