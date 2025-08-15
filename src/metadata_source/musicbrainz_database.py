import json
from typing import Any
from datetime import datetime

import psycopg2

from src.logger import logger
from src.basemodels import Album


class MusicBrainzDataBase:

    def __init__(self) -> None:
        conn = psycopg2.connect(database="musicbrainz", user="Administrator", client_encoding="utf8")
        self.cur = conn.cursor()

    def select_albums(self, release_id: str = None, catalognumber: str = None, 
                      date: str = None) -> list[Album]:
        
        if not any([release_id, catalognumber, date]):
            logger.info("No valid conditions.")
            return []
        
        where_clauses = []
        release_id and where_clauses.append("release_id = %s")
        catalognumber and where_clauses.append("catalognumber = %s")
        date and where_clauses.append("date = %s")
        query_params = [v for v in [release_id, catalognumber, date] if v]

        sql = "SELECT * FROM album WHERE " + " AND ".join(where_clauses)
        
        logger.info(f"Executing Query: {self.cur.mogrify(sql, tuple(query_params)).decode('utf-8')}")

        self.cur.execute(sql, query_params)
        records = self.cur.fetchall()
        albums = [self._record_to_album(r) for r in records]

        logger.info(f"Got {len(albums)} albums.")
        return albums

    def search_albums(self, catalognumber: str = None, date: str = None, album: str = None, 
                     tracks_count: int = None, tracks_abstract: str = None, limit: int = 10) -> list[Album]:

        if not any([catalognumber, date, album, tracks_count, tracks_abstract]):
            logger.info("No valid conditions.")
            return []


        where_clauses = []
        order_clauses = []

        where_params, order_params = [], []

        if catalognumber:
            order_clauses.append("similarity(catalognumber, %s)")
            order_params.append(catalognumber)
        
        if date:
            date_int = sum(MusicBrainzDataBase._date_str_to_range(date)) // 2
            where_clauses.append("((ABS(_date_min - %s) < 366 OR ABS(_date_max - %s) < 366) OR (_date_min = 0 AND _date_max = 0))")
            order_clauses.append("similarity(date, %s)")
            where_params.extend([date_int, date_int])
            order_params.append(date)

        if album:
            order_clauses.append("similarity(album, %s)")
            order_params.append(album)

        if tracks_count is not None:
            where_clauses.append("_tracks_count = %s")
            where_params.append(tracks_count)

        if tracks_abstract:
            order_clauses.append("similarity(_tracks_abstract, %s)")
            order_params.append(tracks_abstract)

        sql = "SELECT * FROM album"

        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        if order_clauses:
            sql += f" ORDER BY ({' + '.join(order_clauses)}) DESC"
        
        sql += f" LIMIT {limit};"

        logger.info(f"Executing Query: {self.cur.mogrify(sql, where_params + order_params).decode('utf-8')}")
        
        self.cur.execute(sql, where_params + order_params)
        records = self.cur.fetchall()
        albums = [self._record_to_album(record) for record in records]

        logger.info(f"Got {len(albums)} albums.")
        return albums

    # 内部方法

    @staticmethod
    def _record_to_album(record: tuple[Any]) -> Album:
        data = {
            "catalognumber": record[2],
            "date": record[3],
            "album": record[4],
            "tracks": json.loads(record[5]),
            "themes": list(record[6]),
            "links": list(record[7])
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



