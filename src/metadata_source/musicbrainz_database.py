from typing import Any
from datetime import datetime

import orjson
import psycopg2
from psycopg2 import extras

from src.logger import logger
from src.common.ongaku_exception import OngakuException
from src.common.basemodels import Album, Track
from src.common.basemodel_utils import abstract_tracks_info


class MusicBrainzDatabase:

    COLUMNS = ["id", 
               "release_id", "catalognumber", "date", "album", "tracks_json", "links", 
               "_date_min", "_date_max", "_tracks_count", "_tracks_abstract"]

    def __init__(self) -> None:

        self.conn = psycopg2.connect(database="musicbrainz", user="Administrator")
        self.cur = self.conn.cursor()

    def insert_albums(self, release_ids: list[str], albums: list[Album]) -> None:
        sql = f'INSERT INTO album ({", ".join(self.COLUMNS[1:])}) VALUES %s;'
        try:
            values = [self._album_to_record(rid, a) for rid, a in zip(release_ids, albums)]
            extras.execute_values(self.cur, sql, values, page_size=len(albums))
            self.conn.commit()
            logger.info(f"Inserted {len(albums)} albums.")
        except Exception:
            self.conn.rollback()
            logger.error("Failed to insert.", exc_info=1)
            raise OngakuException()

    def select_albums(
            self,
            filter_release_id: str = None,
            filter_catalognumber: str = None,
            filter_date: str = None,
            filter_date_int: str = None,
            filter_tracks_count: int = None,
            order_catalognumber: str = None,
            order_album: str = None,
            order_tracks_abstract: str = None,
            limit: int = 10,
            allow_full_scan: bool = False) -> tuple[list[str], list[Album]]:
        """
        :return albums: Album 模型列表
        """

        if not any([filter_release_id, filter_catalognumber, filter_date, filter_date_int, filter_tracks_count, 
                    order_catalognumber, order_album, order_tracks_abstract]):
            logger.info("No valid conditions.")
            return []
        
        # 拦截 全表扫描
        if not any([filter_release_id, filter_catalognumber, filter_date, filter_date_int, filter_tracks_count]):
            if not allow_full_scan:
                logger.info("No filter conditions, and not allow full scan. Return.")
                return []
            else:
                logger.warning("No filter conditions, will scan full table.")

        where_clauses = []
        order_clauses = []
        query_params = []

        if filter_release_id:
            where_clauses.append("release_id = %s")
            query_params.append(filter_release_id)
        
        if filter_catalognumber:
            where_clauses.append("catalognumber = %s")
            query_params.append(filter_catalognumber)
        
        if filter_date:
            where_clauses.append("date = %s")
            query_params.append(filter_date)
        
        if filter_date_int:
            where_clauses.append("((ABS(_date_min - %s) < 182 OR ABS(_date_max - %s) < 182) OR (_date_min = 0 AND _date_max = 0))")
            query_params.extend([filter_date_int, filter_date_int])
        
        if filter_tracks_count:
            where_clauses.append("_tracks_count = %s")
            query_params.append(filter_tracks_count)

        if order_catalognumber:
            order_clauses.append("similarity(catalognumber, %s)")
            query_params.append(order_catalognumber)

        if order_album:
            order_clauses.append("similarity(album, %s)")
            query_params.append(order_album)

        if order_tracks_abstract:
            order_clauses.append("similarity(_tracks_abstract, %s)")
            query_params.append(order_tracks_abstract)

        sql = "SELECT * FROM album"

        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        if order_clauses:
            sql += f" ORDER BY ({' + '.join(order_clauses)}) DESC"
        
        sql += f" LIMIT {limit};"

        logger.info(f"Executing Query: {self.cur.mogrify(sql, query_params).decode('utf-8')}")
        
        self.cur.execute(sql, query_params)
        records = self.cur.fetchall()

        albums = list(map(self._record_to_album, records))

        logger.info(f"Got {len(albums)} albums.")
        return albums

    # 内部方法

    @staticmethod
    def _album_to_record(release_id: str, album: Album) -> tuple[Any]:
        return (
            release_id,
            album.catalognumber,
            album.date,
            album.album,
            orjson.dumps(album.model_dump()["tracks"]).decode("utf-8"),
            "{" + ", ".join(album.links) + "}",
            *MusicBrainzDatabase._date_str_to_range(album.date),
            len(album.tracks),
            abstract_tracks_info(album)
        )

    @staticmethod
    def _record_to_album(record: tuple[Any]) -> Album:
        data = {
            "catalognumber": record[2],
            "date": record[3],
            "album": record[4],
            "tracks": orjson.loads(record[5]),
            "links": list(record[6])
        }
        return Album(**data)
    
    @staticmethod
    def _date_str_to_range(date_str: str) -> tuple[int, int]:
        if not date_str:
            return 0, 0

        reference_date = datetime(1, 1, 1).date()

        parts = date_str.split('-') + [None, None]
        year, month, day = [int(x) if x and x.isdigit() else None for x in parts[:3]]

        if year and month and day:
            _min = _max = datetime(year, month, day).date() - reference_date
            return _min.days, _max.days
        
        if year and month:
            _min = datetime(year, month, 1).date() - reference_date
            _max = datetime(year, month, 28).date() - reference_date
            return _min.days, _max.days
        
        if year:
            _min = datetime(year, 1, 1).date() - reference_date
            _max = datetime(year, 12, 31).date() - reference_date
            return _min.days, _max.days
        
        return 0, 0

