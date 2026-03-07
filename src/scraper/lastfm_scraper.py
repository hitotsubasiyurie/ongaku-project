
from src.core.basemodels import Album, Disc, Track
from src.core.logger import logger, logger_watched
from src.scraper._scraper import Scraper


class LastFMScraper(Scraper):

    ROOT_URL = "https://ws.audioscrobbler.com/2.0"
    PAGE_ROOT_URL = "https://www.last.fm/music"

    def __init__(self, api_key: str) -> None:
        super().__init__()
        self.api_key = api_key

    def get_album_names_from_artist(self, artist: str) -> list[str]:
        names = []
        page = 1

        while True:
            url = f"{self.ROOT_URL}/?method=artist.gettopalbums&api_key={self.api_key}&artist={artist}&page={page}&format=json"
            logger.info(f"Will get artist. {url} page {page}")

            resp = self._cached_request_get(url).json()

            names.extend(self._quote(a["url"].split("/")[-1]) for a in resp["topalbums"]["album"])

            if page >= int(resp["topalbums"]["@attr"]["totalPages"]):
                logger.info(f"Reached the last page. {page}")
                break

            page += 1

        logger.info(f"Artist has {len(names)} albums. {artist} {names}")
        return names

    def get_album(self, artist: str, album: str) -> Album:
        artist, album = self._quote(artist), self._quote(album)
        url = f"{self.ROOT_URL}/?method=album.getinfo&api_key={self.api_key}&artist={artist}&album={album}&format=json"
        logger.info(f"Will get album. {url}")

        resp = self._cached_request_get(url).json()
        track_data = resp["album"].get("tracks", {}).get("track", [])
        track_data = [track_data] if isinstance(track_data, dict) else track_data
        tracks = [Track(tracknumber=t["@attr"]["rank"], title=t["name"], artist=t["artist"]["name"]) 
                  for t in track_data]
        album = Album(album=resp["album"]["name"], tracks=tracks, links=[resp["album"]["url"]])
        return album

    @staticmethod
    def _quote(s: str) -> str:
        """
        """
        # Last.FM album 页面 url 缺少对部分特殊字符的转义
        _map = {"&": "%26"}
        for k, v in _map.items():
            s = s.replace(k, v)
        return s


