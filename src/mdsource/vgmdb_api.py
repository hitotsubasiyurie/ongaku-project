import itertools
import json
import pickle
import re
import uuid
from pathlib import Path

import requests
from lxml import etree

from src.core.basemodels import Album, Disc, Track
from src.core.exception import OngakuException
from src.core.logger import logger, logger_watched
from src.mdsource.common import assemble_albums_from_discs
from src.utils import retry, RateLimiter


class VGMdbAPI:
    
    # 限制频率 1.5 秒 1 次
    _rate_limiter = RateLimiter(interval=1.5)
    # 超时 8 秒
    _REQUEST_TIMEOUT = 8
    
    ROOT_URL = "https://vgmdb.net"
    PRODUCT_PAGE_URL = f"{ROOT_URL}/product/{{}}"
    ALBUM_PAGE_URL = f"{ROOT_URL}/album/{{}}"

    _HEADERS = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        # 界面信息 优先日语
        "cookie": "gfa_lang=ja;"
    }

    def __init__(self, cache_dir: str = None) -> None:
        """
        :param cache_dir: 可选，缓存目录路径
        """
        self._cache_dir = cache_dir

    def get_product_ids_from_franchise(self, franchise_id: str) -> list[str]:
        """
        从 franchise 页面获取 product ids 。\n
        :raises OngakuException:
        """
        url = self.PRODUCT_PAGE_URL.format(franchise_id)
        logger.info(f"Will get franchise. {url}")
        resp = self._cached_request_get(url)
        
        html: etree._Element = etree.HTML(resp.text)
        table = html.xpath("//div[@id='collapse_sub']/div/table")[0]
        product_urls = [a.xpath("@href")[0] for a in table.iter("a")]
        product_urls = [u for u in product_urls if "product/" in u]
        product_ids = [u.split("product/")[1].strip("/") for u in product_urls]

        logger.info(f"Got {len(product_ids)} product ids from franchise {franchise_id}.")
        return product_ids

    def get_product_titles(self, product_id: str) -> list[str]:
        """
        获取 product 的标题，所有语言。\n
        :raises OngakuException:
        """
        url = self.PRODUCT_PAGE_URL.format(product_id)
        resp = self._cached_request_get(url)

        html: etree._Element = etree.HTML(resp.text)
        spans: list[etree._Element] = html.xpath("//div[@id='innermain']//h1//span[@class='albumtitle']")
        titles = list(set(s.xpath("string(.)").strip("/ ") for s in spans))
        logger.info(f"Got product titles. {product_id} {titles}")
        return titles

    def get_album_ids_from_search_page(self, url: str) -> list[str]:
        """
        从搜索页面获取 album ids 。\n
        :raises OngakuException:
        """
        logger.info(f"Will get page. {url}")
        resp = self._cached_request_get(url)

        html: etree._Element = etree.HTML(resp.text)
        album_urls: list[str] = html.xpath("//div[@id='albumresults']/table/tbody/tr/td/a/@href")
        album_ids = [u.split("album/")[1].strip("/") for u in album_urls if "album/" in u]

        logger.info(f"Got {len(album_ids)} album ids from page {url}.")
        return album_ids

    def get_album_ids_from_product(self, product_id: str) -> list[str]:
        """
        从 product 页面获取 album ids 。\n
        :raises OngakuException:
        """
        url = self.PRODUCT_PAGE_URL.format(product_id)
        logger.info(f"Will get product. {url}")
        resp = self._cached_request_get(url)

        html: etree._Element = etree.HTML(resp.text)
        album_urls: list[str] = html.xpath("//div[@id='discotable']/table/tbody/tr/td/a/@href")
        album_ids = [u.split("album/")[1].strip("/") for u in album_urls]

        logger.info(f"Got {len(album_ids)} album ids from product {product_id}.")
        return album_ids

    @logger_watched(3)
    def get_albums(self, album_id: str) -> list[Album]:
        """
        从 album 页面获取 Album 模型列表。\n
        :raises OngakuException:
        """
        url = self.ALBUM_PAGE_URL.format(album_id)
        logger.info(f"Will get album. {url}")

        resp = self._cached_request_get(url)
        html: etree._Element = etree.HTML(resp.text)

        album_title = html.xpath("//div[@id='innermain']//h1//span[@class='albumtitle' and @style='display:inline']"
                                 )[0].xpath("string(.)").strip("/ ")
        logger.info(f"Got album title. {[album_title]}")

        info_table = html.xpath("//div[@id='rightfloat']//table[@id='album_infobit_large']")[0]
        album_info = self._get_album_info(info_table)
        catnos = self._expand_catno(album_info.get("Catalog Number"))
        date = self._convert_date(album_info.get("Release Date", ""))

        # 音轨信息优先日语，其次第一个元素
        tl_id: etree._Element = html.xpath("//ul[@class='tabnav']//a[text()='Japanese']/@rel") \
            or html.xpath("//ul[@class='tabnav']//a[1]/@rel")

        # https://vgmdb.net/album/105234 tracklist 为空
        if not tl_id:
            logger.warning(f"No tracklist span. {url}")
            return assemble_albums_from_discs(catnos, date, album_title, [], url)

        tl_span: etree._Element = html.xpath(f"//span[@class='tl' and @id='{tl_id[0]}']")[0]
        discs = self._get_discs(tl_span)

        return assemble_albums_from_discs(catnos, date, album_title, discs, url)

    ####################### 内部方法 ######## ################

    @staticmethod
    def _get_album_info(info_table: etree._Element) -> dict:
        """
        从 info_table 元素获取专辑信息。\n
        """
        table = [list(tr.iterchildren("td")) for tr in info_table.iterchildren("tr")]
        infos = {tds[0].xpath("string(.)").strip(): tds[1].xpath("string(.)").strip() for tds in table if tds}
        logger.debug(f"Got album info. {json.dumps(infos, ensure_ascii=False)}")

        # https://vgmdb.net/album/144196  catno 元素包含多余信息
        if "Catalog Number" in infos:
            infos["Catalog Number"] = infos["Catalog Number"].split()[0].strip()
        return infos

    def _get_discs(self, tl_span: etree._Element) -> list[Disc]:
        """
        从 tl_span 元素获取 Disc 模型列表。\n
        :raises OngakuException:
        """
        logger.info(f"Will get discs.")

        # 选择 table 和 table 的前一个 span 构造 元素列表
        # [span, table, ..., span, table]
        elements = tl_span.xpath(".//table | .//table/preceding-sibling::span[1]")
        logger.info(list(e.tag for e in elements))
        # elements 奇数个 或者 奇数位不是 span 或者 偶数位不是 table
        if len(elements) & 1 or any(e.tag != "table" for e in elements[1::2]) or any(e.tag != "span" for e in elements[::2]):
            logger.error(f"Failed to parse tracklist span.")
            raise OngakuException()

        discs = []
        for i, (span, table) in enumerate(itertools.batched(elements, 2)):
            disc_title = span.xpath("string(.)").strip()
            disc = Disc(discnumber=i+1, disc=disc_title, tracks=self._get_tracks(table))
            discs.append(disc)
            logger.info(f"Got disc {disc.discnumber} {[disc.disc]}, with {len(disc.tracks)} tracks.")

        logger.info(f"Got {len(discs)} discs. {[d.disc for d in discs]}")
        return discs

    @staticmethod
    def _get_tracks(table: etree._Element) -> list[Track]:
        """
        从 table 元素获取 Track 模型列表。\n
        :raises OngakuException:
        """
        # https://vgmdb.net/album/135468
        # https://vgmdb.net/album/122066
        tracks = []
        for tr in table.iterchildren("tr"):
            tds: list[etree._Element] = list(tr.iterchildren("td"))
            if len(tds) < 2:
                continue
            tracknumber = tds[0].xpath("string(.)").strip()
            tracknumber = int(tracknumber) if tracknumber.isdigit() else None
            track_title = tds[1].xpath("string(.)").strip()
            tracks.append(Track(tracknumber=tracknumber, title=track_title))
            if not tracknumber or not track_title:
                logger.warning(f"Failed to get track. {tracknumber, track_title}")
        logger.info(f"Got {len(tracks)} tracks. {[t.title for t in tracks]}")
        return tracks

    @staticmethod
    def _expand_catno(catno: str) -> list[str]:
        """
        将省略的 catno 扩展成 catno 列表。
        1. catno 为空时返回空列表。
        2. catno 无法解析时返回 [catno] 。\n
        :param catno: 形如 SVWC-70509, SVWC-70509~12
        """
        if not catno or catno.upper() in ["N/A", "N／A"]:
            return []

        if catno.count("~") == 0:
            logger.info(f"No need to expand catno: {[catno]}")
            return [catno]

        # https://vgmdb.net/album/125187 catno 多余字符
        # https://vgmdb.net/album/121652 多个 ~
        if catno.count("~") > 1:
            logger.warning(f"Failed to parse catno. {[catno]}")
            return [catno]

        base_catno, r2 = catno.split("~")
        digit_length = len(r2)
        prefix, r1 = base_catno[:-len(r2)], base_catno[-len(r2):]

        if not r1.isdigit() or not r2.isdigit():
            logger.warning(f"Failed to parse catno. {[catno]}")
            return [catno]

        r1, r2 = int(r1), int(r2)
        catnos = [prefix + str(r).zfill(digit_length) for r in range(r1, r2 + 1)]
        logger.info(f"Expanded {[catno]} to {catnos}")
        return catnos

    @staticmethod
    def _convert_date(date: str) -> str:
        """
        :param date: 如 "Dec 05, 2018", "Dec 2018", "2018"
        :return: 标准格式，如 "2018-12-05"
        """
        months = ["_", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        # 匹配 如 "Dec 05, 2018"
        match = re.search(r"(\w{3})\s(\d{2}),\s(\d{4})", date)
        if match and match.group(1) in months:
            return f"{match.group(3)}-{str(months.index(match.group(1))).zfill(2)}-{match.group(2)}"
        # 匹配 如 "Dec 2018"
        match = re.search(r"(\w{3})\s(\d{4})", date)
        if match and match.group(1) in months:
            return f"{match.group(2)}-{str(months.index(match.group(1))).zfill(2)}"
        # 匹配 如 "2018"
        match = re.search(r"(\d{4})", date)
        if match:
            return match.group(1)
        logger.warning(f"Failed to parse date. {date}")
        return date

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
        return requests.get(url, timeout=VGMdbAPI._REQUEST_TIMEOUT, headers=VGMdbAPI._HEADERS)

