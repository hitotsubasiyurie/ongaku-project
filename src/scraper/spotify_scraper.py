import itertools
import json
import re
from functools import cached_property

import requests

from src.core.basemodels import Album, Disc, Track
from src.core.exception import OngakuException
from src.core.logger import logger, logger_watched
from src.scraper._scraper import Scraper
from src.core.settings import g_settings


class SpotifyScraper(Scraper):

    ALBUM_PAGE_URL = "https://open.spotify.com/album/{}"

    def __init__(self, client_id: str, client_secret: str) -> None:
        super().__init__()
        self.client_id = client_id
        self.client_secret = client_secret

    @cached_property
    def access_token(self) -> str:
        data = {"grant_type": "client_credentials", "client_id": self.client_id, "client_secret": self.client_secret}
        resp = requests.post("https://accounts.spotify.com/api/token", data=data)
        access_token = resp.json()["access_token"]
        logger.info(f"access_token: {access_token}")
        return access_token

    def get_albums(self, album_id: str) -> list[Album]:
        url = f"https://api.spotify.com/v1/albums/{album_id}"
        logger.info(f"Will get album. {url}")

        headers = {"Authorization": f"Bearer  {self.access_token}"}
        resp = self._cached_request_get(url, headers=headers)
        print(resp.text)

        discs = self._get_discs(resp)
        return self.split_multi_disc_album(catnos=[], date=resp["release_date"], 
                                           album_title=resp["name"], discs=discs, link=self.ALBUM_PAGE_URL.format(album_id))

    def _get_discs(self, resp: dict) -> list[Disc]:
        discs = []

        items = list(sorted(resp["tracks"]["items"], key=lambda i: i["disc_number"]))
        for k, g in itertools.groupby(items, key=lambda i: i["disc_number"]):
            tracks = []
            
            for item in g:
                artist = ", ".join(a["name"] for a in item["artists"])
                track = Track(tracknumber=item["track_number"], title=item["name"], artist=artist)
                tracks.append(track)
            
            disc = Disc(discnumber=k, tracks=tracks)
            discs.append(disc)

        return discs


scraper = SpotifyScraper("ac732f3cda584512805c0efc6894d017", "cc9a2886489a4296870e110efef43572")
print(scraper.get_albums("5hFSXGg9nK6Bbq5lvAS8cb"))

