from functools import cache

import orjson
from rapidfuzz import fuzz

from src.common.basemodels import Album, Track

# 缓存
@cache
def album_to_unique_str(a: Album) -> str:
    return orjson.dumps([a.catalognumber, a.date, a.album, len(a.tracks)]).decode("utf-8")


def abstract_tracks_info(album: Album) -> str:
    """
    摘要 tracks 信息。
    """
    return "\n".join(f"{t.tracknumber}. {t.title}" for t in album.tracks)


def count_track_similarity(a: Track, b: Track) -> float:
    """
    计算两个 Track 的相似度。
    """
    ratio = fuzz.ratio(f"{a.tracknumber}. {a.title}", f"{b.tracknumber}. {b.title}")
    if a.artist and b.artist:
        ratio += fuzz.ratio(None, a.artist, b.artist)
        return ratio / 2
    return ratio


def count_album_similarity(a: Album, b: Album) -> float:
    """
    计算两个 Album 的相似度。
    """
    ratio = (fuzz.ratio(a.catalognumber, b.catalognumber) + 
             fuzz.ratio(a.date, b.date) + 
             fuzz.ratio(a.album, b.album) + 
             fuzz.ratio(abstract_tracks_info(a), abstract_tracks_info(b)))
    ratio = ratio / 4
    return ratio

