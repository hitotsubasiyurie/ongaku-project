import pickle
import uuid
from pathlib import Path
from collections import Counter

import requests

from src.core.basemodels import Album, Disc
from src.core.logger import logger
from src.core.settings import global_settings
from src.utils import retry, RateLimiter


class Scraper:

    # 请求 间隔 1.5 秒
    _REQUEST_INTERVAL = 1.5
    # 请求 超时 8 秒
    _REQUEST_TIMEOUT = 8
    # 请求 重试 10 次
    _REQUEST_RETRY_TIMES = 10
    # 请求 重试间隔 5 秒
    _REQUEST_RETRY_DELAY = 5
    # 请求 缓存 位置
    _REQUEST_CACHE_PATH = Path(global_settings.temp_directory, "request_cache")
    # 请求 请求头
    _REQUEST_HEADERS = None

    def __init__(self) -> None:
        self.__rate_limiter = RateLimiter(self._REQUEST_INTERVAL)
        self.__request_get = retry(self._REQUEST_RETRY_TIMES, self._REQUEST_RETRY_DELAY)(self.__rate_limiter(requests.get))
        # 创建 缓存目录
        not self._REQUEST_CACHE_PATH.is_dir() and self._REQUEST_CACHE_PATH.mkdir(parents=True)

    @staticmethod
    def split_multi_disc_album(catnos: list[str], date: str, album_title: str, discs: list[Disc], link: str) -> list[Album]:
        """
        将多碟专辑拆分为独立的专辑。

        | catno | discs | Album |   | |
        |-------|-------|-------|---|-|
        | 0     | 0     | 1     |   | 1 张专辑，无 catno 无 tracks |
        | 0     | 1     | 1     |   | 1 张专辑，无 catno |
        | 0     | n     | n     |   | n 张专辑，无 catno |
        | 1     | 0     | 1     |   | 1 张专辑，无 tracks |
        | 1     | 1     | 1     |   | 1 张专辑 |
        | 1     | n     | n     |   | n 张专辑 |
        | n     | 0     | n     |   | n 张专辑，无 tracks |
        | n     | 1     | 1     | × | 1 张专辑，无法确定 catno |
        | n     | n     | n     |   | n 张专辑 |
        | n     | n < m | m     | × | m 张专辑，无法确定 catno |
        | n     | n > m | n     | × | m 张专辑，无法确定 catno |
        """
        if len(catnos) <= 1 and len(discs) <= 1:
            albums = [Album(catalognumber=catnos[0] if catnos else "", date=date, album=album_title,
                                    tracks=discs[0].tracks if discs else [], links=[link])]
        elif len(catnos) <= 1:
            albums = [Album(catalognumber=catnos[0] if catnos else "", date=date,
                                        album=f"{album_title} {d.disc}", tracks=d.tracks, links=[link])
                        for d in discs]
        elif len(discs) == 0:
            albums = [Album(catalognumber=c, date=date, album=album_title, tracks=[], links=[link]) for c in catnos]
        elif len(catnos) == len(discs):
            albums = [Album(catalognumber=c, date=date, album=f"{album_title} {d.disc}", tracks=d.tracks, links=[link])
                        for c, d in zip(catnos, discs)]
        else:
            logger.warning(f"Failed to assign albums. {catnos, date, album_title}")
            albums = [Album(catalognumber=", ".join(catnos), date=date, album=f"{album_title} {d.disc}", 
                            tracks=d.tracks, links=[link])
                        for d in discs]
        
        # 处理同名专辑
        _count = Counter([a.album for a in albums])
        for i, a in enumerate(albums):
            if _count[a.album] > 1:
                a.album += f" Disc {i+1}"

        logger.info(f"Got {len(albums)} albums. {[(a.catalognumber, a.album) for a in albums]}")
        return albums

    def _cached_request_get(self, url: str, **kwargs) -> requests.Response:
        """
        带缓存的 request.get 。
        """
        cache = Path(self._REQUEST_CACHE_PATH, str(uuid.uuid5(uuid.NAMESPACE_URL, name=url)))
        if cache.exists():
            logger.debug(f"In cache. {url}")
            return pickle.loads(cache.read_bytes())
        resp = self.__request_get(url, **kwargs, timeout=self._REQUEST_TIMEOUT, headers=self._REQUEST_HEADERS)
        cache.write_bytes(pickle.dumps(resp))
        return resp





