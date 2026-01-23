import pickle
import pickle
import re
import uuid
from pathlib import Path

import requests
from lxml import etree

from src.core.basemodels import Album, Track
from src.core.logger import logger
from src.scraper._scraper import Scraper


class DoujinMusicInfoScraper(Scraper):

    ROOT_URL = "https://www.dojin-music.info"
    CIRCLE_PAGE_URL = f"{ROOT_URL}/circle/{{}}"
    CD_PAGE_URL = f"{ROOT_URL}/cd/{{}}"

    _HEADERS = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    }

    def get_cd_ids_from_circle(self, circle_id: str) -> None:
        """
        从 circle 页面获取 cd ids 。\n
        :raises OngakuException:
        """
        url = self.CIRCLE_PAGE_URL.format(circle_id)
        logger.info(f"Will get circle. {url}")
        resp = self._cached_request_get(url)
        html: etree._Element = etree.HTML(resp.text)

        detail_ul = html.xpath("//ul[@id='circle_detail_cdList']")[0]
        cd_urls = detail_ul.xpath("//ul[@id='circle_detail_cdList']//a/@href")
        cd_urls = [u for u in cd_urls if "cd/" in u]
        cd_ids = [u.split("cd/")[1] for u in cd_urls]
        logger.info(f"Got {len(cd_ids)} cd ids from circle {circle_id}.")
        return cd_ids

    def get_album_from_cd(self, cd_id: str) -> Album:
        """
        从 cd 页面获取 Album 模型。\n
        :raises OngakuException:
        """
        url = self.CD_PAGE_URL.format(cd_id)
        logger.info(f"Will get cd. {url}")
        resp = self._cached_request_get(url)
        html: etree._Element = etree.HTML(resp.text)


        album_title = html.xpath("//div[@id='cd_detail']/h1")[0].xpath("string(.)")

        detail = html.xpath("//div[@id='cd_detail_header']")[0].xpath("string(.)")
        search = re.search(r"頒布開始日：([0-9/]+)", detail)
        date = self._convert_date(search.group(1)) if search else ""

        return Album(catalognumber="", date=date, album=album_title, 
                     tracks=self._get_tracks(html), links=[url])

    # 内部方法

    @staticmethod
    def _get_tracks(html: etree._Element) -> list[Track]:
        """
        从 html 元素获取 Track 模型列表。\n
        :raises OngakuException:
        """
        tracks = []
        for i, li in enumerate(html.xpath("//ul[@id='cd_detail_songList']/li")):
            title = li.xpath(".//dt")[0].xpath("string(.)")
            string = li.xpath(".//dd")[0].xpath("string(.)")
            # https://www.dojin-music.info/cd/6336
            if "歌：" in string:
                artist = re.split(r"編曲：|作詞：|作曲：", string.split("歌：")[1])[0]
            else:
                logger.warning(f"Not found artist. {string}")
                artist = ""
            tracks.append(Track(tracknumber=i+1, title=title, artist = artist))

        logger.info(f"Got {len(tracks)} tracks. {[t.title for t in tracks]}")
        return tracks

    @staticmethod
    def _convert_date(date: str) -> str:
        """
        :param date: 如 "2008/12/29", 
        :return: 标准格式，如 "2018-12-05"
        """
        return date.replace("/", "-")




