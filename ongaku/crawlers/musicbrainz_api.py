import itertools
import pickle
import re
import uuid
from pathlib import Path
from typing import Literal

import requests

from ongaku.core.logger import logger, logger_watched
from ongaku.core.basemodels import Album, Disc, Track
from ongaku.utils.utils import retry, RateLimiter
from ongaku.crawlers.vgmdb_api import VGMdbAPI


_LUCENE_ESCAPE_RE = re.compile(r'([+\-&|!(){}\[\]^"~*?:\\/])')


class MusicBrainzAPI:

    # 限制频率 1.5 秒 1 次
    _rate_limiter = RateLimiter(interval=1.5)
    # 超时 8 秒
    _REQUEST_TIMEOUT = 8

    ROOT_URL = "https://musicbrainz.org/ws/2"
    RELEASE_PAGE_URL = "https://beta.musicbrainz.org/release/{}"
    
    _HEADERS = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"}

    def __init__(self, cache_dir: str = None) -> None:
        """
        :param cache_dir: 可选，缓存目录路径
        """
        self._cache_dir = cache_dir

    def query_albums(self, catno: str = None, date: str = None, release: str = None, tracks_number: int = None,
                      limit: int = 5) -> list[Album]:
        """
        :param catno:
        :param date: 必须如 2020-01-15
        :param release: 标题
        :param tracks_number: 音轨数
        :param limit: 返回结果数，默认 5
        :return albums:
        """
        if not any([catno, date, release, tracks_number]):
            logger.info(f"No valid param to query. Return.")
            return []
        lst = []
        release and lst.append("release:{}".format(_LUCENE_ESCAPE_RE.sub(r"\\\1", release)))
        catno and lst.append("catno:{}".format(_LUCENE_ESCAPE_RE.sub(r"\\\1", catno)))
        date and lst.append("date:{}".format(_LUCENE_ESCAPE_RE.sub(r"\\\1", date)))
        tracks_number and lst.append(f"tracks:{tracks_number}")

        url = f"{self.ROOT_URL}/release/?fmt=json&limit={limit}&query={' AND '.join(lst)}"
        logger.info(f"search url: {url}")

        resp = self._cached_request_get(url)

        query = resp.json()
        if query["count"] == 0:
            logger.warning(f"No releases queried.")
            return []
        
        albums = list(itertools.chain.from_iterable(self.get_album_from_release(r["id"]) for r in query["releases"]))
        logger.info(f"Queried {len(albums)} albums.")
        return albums

    @logger_watched(3)
    def get_albums_from_series(self, series_id: str) -> list[Album]:
        """
        给定 series mbid 获取 Album 模型列表。\n
        raises: OngakuException
        """
        albums = []
        series = self.lookup_entity("series", series_id)
        rg_ids = [r["release_group"]["id"] for r in series["relations"]]
        logger.info(f"Series has {len(rg_ids)} release-groups. {series_id} {rg_ids}")

        [albums.extend(self.get_albums_from_release_group(rg_id)) for rg_id in rg_ids]

        logger.info(f"Got {len(albums)} albums from series {series_id}.")
        return albums

    @logger_watched(2)
    def get_albums_from_release_group(self, rg_id: str) -> list[Album]:
        """
        给定 release-group mbid 获取 Album 模型列表。\n
        raises: OngakuException
        """
        albums = []
        release_group = self.lookup_entity("release-group", rg_id)
        r_ids = [r["id"] for r in release_group["releases"]]
        logger.info(f"Release-group has {len(r_ids)} releases. {rg_id} {r_ids}")

        [albums.extend(self.get_album_from_release(r_id)) for r_id in r_ids]

        logger.info(f"Got {len(albums)} albums from release-group {rg_id}.")
        return albums

    @logger_watched(1)
    def get_album_from_release(self, release_id: str) -> list[Album]:
        """
        给定 release mbid 获取 Album 模型列表。\n
        raises: OngakuException
        """
        logger.info(f"Will get album. {release_id}")
        release = self._get_release_with_recordings(release_id)

        albums = self._build_album_from_release(release)
        logger.info(f"Got {len(albums)} albums from release {release_id}.")
        return albums

    def lookup_entity(self, entity_type: Literal["series", "release-group", "release"], mbid: str) -> dict:
        """
        调用 lookup api 。\n
        """
        inc = {"series": "release-group-rels", "release-group": "release-group-rels", "release": "recordings+labels"}
        url = f"{self.ROOT_URL}/{entity_type}/{mbid}?fmt=json&inc={inc[entity_type]}"
        logger.info(f"Lookup {entity_type}. {url}")

        resp = self._cached_request_get(url)
        return resp.json()

    # 内部方法

    def _browse_recordings_of_release(self, release_id: str) -> list[dict]:
        """
        浏览 release 的所有 recordings 。\n
        """
        recordings = []
        limit, offset = 100, 0

        while True:
            url = f"{self.ROOT_URL}/recording?release={release_id}&fmt=json&inc=artist-credits&limit={limit}&offset={offset}"
            logger.info(f"Browse recordings of release. {url}")

            resp = self._cached_request_get(url)

            browse = resp.json()
            recordings.extend(browse["recordings"])
            logger.info(f"This page has {len(browse["recordings"])} recordings. {limit} {offset}")

            if browse["recording-count"] <= offset + limit:
                logger.info(f"Reached the last page. {limit} {offset}")
                break
            
            offset += limit
            logger.info(f"Not the last page. {limit} {offset}")

        logger.info(f"Got {len(recordings)} recordings of release {release_id}.")
        return recordings

    def _get_release_with_recordings(self, release_id: str) -> dict:
        """
        获取带有 recordings 信息的 release 。\n
        """
        release = self.lookup_entity("release", release_id)
        recordings = self._browse_recordings_of_release(release_id)

        _dict = {r["id"]: r for r in recordings}

        for media in release["media"]:
            for track in media.get("tracks", []):
                track["recording"].update(_dict[track["recording"]["id"]])

        logger.info(f"Updated release recordings.")
        return release

    @staticmethod
    def _build_album_from_release(release: dict) -> list[Album]:
        """
        从带有 recordings 信息的 release 中构造 Album 模型列表。\n
        """
        # catnos 不进行 "none" 字符过滤，以免影响专辑分配
        catnos = [l["catalog-number"] for l in release["label-info"] if l["catalog-number"]]
        
        date = release.get("date", "")
        # 处理 2011-0?-14
        if "?" in date:
            date = "-".join(date.split("?")[0].split("-")[:-1])

        title = release["title"]

        discs = sorted(MusicBrainzAPI._build_disc_from_release(release), key=lambda d: d.discnumber)

        url = MusicBrainzAPI.RELEASE_PAGE_URL.format(release["id"])
        return VGMdbAPI._assemble_albums(catnos, date, title, discs, url)

    @staticmethod
    def _build_disc_from_release(release: dict) -> list[Disc]:
        """
        从带有 recordings 信息的 release 中构造 Disc 模型列表。\n
        """
        disc_models = []
        for media in release["media"]:
            track_models = []

            for track in media.get("tracks", []):
                track_model = Track(tracknumber=track["position"],title=track["title"],
                    artist="".join(itertools.chain(*[[c["name"], c["joinphrase"]] for c in track["recording"]["artist-credit"]])))
                track_models.append(track_model)
            disc_model = Disc(discnumber=media["position"], disc=media["title"], tracks=track_models)
            logger.info(f"Got {len(track_models)} tracks. {[t.title for t in track_models]}")
            logger.info(f"Got disc {disc_model.discnumber} {disc_model.disc}.")
            disc_models.append(disc_model)

        logger.info(f"Got {len(disc_models)} discs from release. {[d.disc for d in disc_models]}")
        return disc_models

    def _cached_request_get(self, url: str) -> requests.Response:
        """
        带缓存的 request.get 。
        """
        cache = Path(self._cache_dir, str(uuid.uuid5(uuid.NAMESPACE_URL, name=url)))
        if cache.exists():
            logger.debug(f"In cache. {url}")
            return pickle.loads(cache.read_bytes())
        resp = self._request_get(url)
        cache.write_bytes(pickle.dumps(resp))
        return resp
    
    @retry(10, delay=5)
    @_rate_limiter
    def _request_get(self, url: str) -> requests.Response:
        return requests.get(url, timeout=MusicBrainzAPI._REQUEST_TIMEOUT, headers=MusicBrainzAPI._HEADERS)

