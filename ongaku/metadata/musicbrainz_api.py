import itertools
import json
import pickle
import re
import time
import uuid
from collections import defaultdict
from functools import cache
from pathlib import Path
from threading import Lock
from typing import Literal

import orjson
import requests

from ongaku.logger import logger, logger_watched
from ongaku.common.metadata import Album, Disc, Track
from ongaku.common.utils import retry
from ongaku.metadata.vgmdb_api import VGMdbAPI


class MusicBrainzAPI:

    # 每分钟 45 次
    _REQUEST_INTERVAL = 1.5
    _REQUEST_TIMEOUT = 5

    ROOT_URL = "https://musicbrainz.org/ws/2"
    _RELEASE_PAGE_URL = "https://beta.musicbrainz.org/release"
    _LUCENE_ESCAPE_RE = re.compile(r'([+\-&|!(){}\[\]^"~*?:\\/])')

    _HEADERS = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"}

    def __init__(self, cache_dir: str, album_db: str = None) -> None:
        """
        :param cache_dir: 缓存目录路径
        """
        self._cache_dir = cache_dir
        self._album_db = album_db
        self._request_lock = Lock()
        self._last_request_time = 0

    def query_release(self, catno: str = None, date: str = None, release: str = None, tracks_number: int = None,
                      limit: int = 5) -> list[Album]:
        """
        :param catno:
        :param date: 必须如 2020-01-15
        :param release: 标题
        :param tracks_number: 音轨数
        :param limit: 返回结果数，默认 5
        :return:
        """
        lst = []
        release and lst.append("release:{}".format(self._LUCENE_ESCAPE_RE.sub(r"\\\1", release)))
        catno and lst.append("catno:{}".format(self._LUCENE_ESCAPE_RE.sub(r"\\\1", catno)))
        date and lst.append("date:{}".format(self._LUCENE_ESCAPE_RE.sub(r"\\\1", date)))
        tracks_number and lst.append(f"tracks:{tracks_number}")

        url = f"{self.ROOT_URL}/release/?fmt=json&limit={limit}&query={' AND '.join(lst)}"
        logger.info(f"search url: {url}")

        resp = self.__request_get_with_cache(url)
        logger.debug(resp.text)

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
        从 series 获取专辑模型列表。
        raises: OngakuException
        """
        albums = []
        series = self.lookup_entity("series", series_id)
        rg_ids = [r["release_group"]["id"] for r in series["relations"]]
        logger.info(f"Series has {len(rg_ids)} release-groups. {series_id} {rg_ids}")

        [albums.extend(self.get_albums_from_release_group(rg_id)) for rg_id in rg_ids]

        logger.info(f"Got {len(albums)} albums from series {series_id}.")
        logger.debug(albums)
        return albums

    @logger_watched(2)
    def get_albums_from_release_group(self, rg_id: str) -> list[Album]:
        """
        从 release-group 获取专辑模型列表。
        raises: OngakuException
        """
        albums = []
        release_group = self.lookup_entity("release-group", rg_id)
        r_ids = [r["id"] for r in release_group["releases"]]
        logger.info(f"Release-group has {len(r_ids)} releases. {rg_id} {r_ids}")

        [albums.extend(self.get_album_from_release(r_id)) for r_id in r_ids]

        logger.info(f"Got {len(albums)} albums from release-group {rg_id}.")
        logger.debug(albums)
        return albums

    @logger_watched(1)
    def get_album_from_release(self, release_id: str, latest: bool = False) -> list[Album]:
        """
        从 release 获取专辑模型列表。
        raises: OngakuException
        """
        if self._album_db and not latest:
            albums = self._get_album_from_album_db(release_id)
            if albums:
                return albums
        
        logger.info("Will get album from internet.")
        link = f"{self._RELEASE_PAGE_URL}/{release_id}"
        release = self._get_release_with_recordings(release_id)

        catnos = [l["catalog-number"] for l in release["label-info"] if l["catalog-number"]]
        catnos = [c for c in catnos if c not in ["[none]"]]
        
        discs = sorted(self._get_disc_from_release(release), key=lambda d: d.discnumber)

        return VGMdbAPI._assemble_albums(catnos, release.get("date", ""), release["title"], discs, link)

    def lookup_entity(self, entity_type: Literal["series", "release-group", "release"], mbid: str) -> dict:
        """调用 lookup api 。"""
        inc = {"series": "release-group-rels", "release-group": "release-group-rels", "release": "recordings+labels"}
        url = f"{self.ROOT_URL}/{entity_type}/{mbid}?fmt=json&inc={inc[entity_type]}"
        logger.info(f"Lookup {entity_type}. {url}")

        resp = self.__request_get_with_cache(url)
        logger.debug(resp.text)
        return resp.json()

    def browse_recordings_of_release(self, release_id: str) -> list[dict]:
        """浏览 release 的所有 recordings 。"""
        recordings = []
        limit, offset = 100, 0

        while True:
            url = f"{self.ROOT_URL}/recording?release={release_id}&fmt=json&inc=artist-credits&limit={limit}&offset={offset}"
            logger.info(f"Browse recordings of release. {url}")

            resp = self.__request_get_with_cache(url)
            logger.debug(resp.text)

            browse = resp.json()
            recordings.extend(browse["recordings"])
            logger.info(f"This page has {len(browse["recordings"])} recordings. {limit} {offset}")

            if browse["recording-count"] <= offset + limit:
                logger.info(f"Reached the last page. {limit} {offset}")
                break
            
            offset += limit
            logger.info(f"Not the last page. {limit} {offset}")

        logger.debug(json.dumps(recordings, ensure_ascii=False))
        return recordings

    def process_mb_database(recording_db: str, release_db: str, album_db: str) -> None:
        """处理 mb 数据库。"""
        recording_db, release_db, album_db = Path(recording_db), Path(release_db), Path(album_db)
        wf = album_db.open("w", encoding="utf-8")

        with recording_db.open(encoding="utf-8") as f:
            recordings = {r["id"]: r for r in map(orjson.loads, f)}

        with release_db.open(encoding="utf-8") as f:
            for release in map(orjson.loads, f):
                [track["recording"].update(recordings.get(track["recording"]["id"], {})) 
                 for media in release["media"] for track in media.get("tracks", [])]
                
                link = f"{MusicBrainzAPI._RELEASE_PAGE_URL}/{release['id']}"
                catnos = [l["catalog-number"] for l in release["label-info"] if l["catalog-number"]]
                discs = sorted(MusicBrainzAPI._get_disc_from_release(release), key=lambda d: d.discnumber)

                albums = VGMdbAPI._assemble_albums(catnos, release.get("date", ""), release["title"], discs, link)
                wf.write("\n".join(a.model_dump_json() for a in albums) + "\n")
                not int(time.time()) % 10 and wf.flush()

        wf.close()

    def _get_album_from_album_db(self, release_id: str) -> list[Album]:
        index = self._get_album_db_index()
        if release_id not in index:
            return []
        albums = []
        with open(self._album_db, "rb") as f:
            for position in sorted(index[release_id]):
                s, e = position
                f.seek(s)
                albums.append(Album(**orjson.loads(f.read(e-s))))
        return albums

    @cache
    def _get_album_db_index(self) -> dict[str, list[tuple[int, int]]]:
        index_path = Path(self._album_db).parent / "album.index"

        if index_path.exists():
            return pickle.loads(index_path.read_bytes())
        
        index = defaultdict(list)
        with open(self._album_db, "rb") as f:
            start = 0
            for line in f:
                end = start + len(line)
                link = orjson.loads(line)["links"][0]
                release_id = link.split("/")[-1]
                index[release_id].append((start, end))
                start = end

        index_path.write_bytes(pickle.dumps(index))
        return index

    def _get_release_with_recordings(self, release_id: str) -> dict:
        """获取拥有 recordings 信息的 release 。"""
        release = self.lookup_entity("release", release_id)
        recordings = self.browse_recordings_of_release(release_id)

        logger.info(f"Will update release.")
        _dict = {r["id"]: r for r in recordings}
        [track["recording"].update(_dict[track["recording"]["id"]]) for media in release["media"] for track in media.get("tracks", [])]
        logger.info(f"Updated release successfully.")
        logger.debug(json.dumps(release, ensure_ascii=False))
        return release

    @staticmethod
    def _get_disc_from_release(release: dict) -> list[Disc]:
        """从已更新的 release 信息中获取 Disc 模型列表。"""
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

    @retry(10, delay=6)
    def __request_get_with_cache(self, url: str) -> requests.Response:
        """带缓存的 request.get 。"""
        cache = Path(self._cache_dir, str(uuid.uuid5(uuid.NAMESPACE_URL, name=url)))
        if cache.exists():
            logger.debug(f"In cache. {url}")
            return pickle.loads(cache.read_bytes())
        with self._request_lock:
            wait = self._last_request_time + self._REQUEST_INTERVAL - time.time()
            wait > 0 and time.sleep(wait)
            resp = requests.get(url, timeout=self._REQUEST_TIMEOUT, headers=self._HEADERS)
        cache.write_bytes(pickle.dumps(resp))
        return resp

