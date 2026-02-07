"""
定义专辑元数据的数据模型
基本元数据：
catalognumber, date, album, tracknumber, title, artist
自定义元数据：
links, mark
"""

import re
from enum import IntEnum

from attrs import define, field, validators


_DATE_PATTERN = re.compile(r"^$|^\d{4}$|^\d{4}-\d{2}$|^\d{4}-\d{2}-\d{2}$")


class TrackMark(IntEnum):
    """音轨标记"""
    # 没有听过
    UNKNOWN = -1
    # 听过
    LISTENED = 0
    # 喜爱
    FAVOURITE = 1


def _convert_string(value: str) -> str:
    """
    1. 去除首尾空字符
    """
    return value.strip()


def _convert_string_tuple(value: tuple[str, ...]) -> tuple[str, ...]:
    """
    1. _convert_string
    2. 元组去重
    3. 元组排序
    """
    return tuple(sorted(set(map(_convert_string, value))))


def _convert_track_tuple(value: tuple["Track", ...]) -> tuple["Track", ...]:
    """
    1. 元组按照 Track.tracknumber 排序
    """
    return tuple(sorted(value, key=lambda t: t.tracknumber))


@define(slots=True, frozen=True, cache_hash=True)
class Track:
    """
    Track 只读模型。

    :param tracknumber: 序号
    :param title: 标题
    :param artist: 艺术家
    :param mark: 音轨标记信息
    """
    tracknumber: int = field(default=0, validator=validators.and_(validators.instance_of(int), validators.ge(0)))
    title: str = field(default="", converter=_convert_string, validator=validators.instance_of(str))
    artist: str = field(default="", converter=_convert_string, validator=validators.instance_of(str))
    mark: TrackMark = field(default=TrackMark.UNKNOWN, validator=validators.in_(TrackMark))


@define(slots=True, frozen=True, cache_hash=True)
class Disc:
    """
    Disc 只读模型。

    :param discnumber: 序号
    :param title: 标题
    :param tracks: Track 模型列表。按照 Track.tracknumber 升序
    """
    discnumber: int = field(default=0, validator=validators.and_(validators.instance_of(int), validators.ge(0)))
    title: str = field(default="", converter=_convert_string, validator=validators.instance_of(str))
    tracks: tuple[Track, ...] = field(default=(), 
                                      converter=_convert_track_tuple,
                                      validator=validators.deep_iterable(
                                          member_validator=validators.instance_of(Track), 
                                          iterable_validator=validators.instance_of(tuple)))


@define(slots=True, frozen=True, cache_hash=True)
class Album:
    """
    Album 只读模型。

    :param catalognumber: 目录编号
    :param date: 日期。仅允许四种模式： ["", "2005", "2005-01", "2005-01-01"]
    :param album: 专辑名
    :param tracks: Track 模型列表。按照 Track.tracknumber 升序
    :param links: 链接列表。升序
    """
    catalognumber: str = field(default="", converter=_convert_string, validator=validators.instance_of(str))
    date: str = field(default="", converter=_convert_string, validator=validators.matches_re(_DATE_PATTERN))
    album: str = field(default="", converter=_convert_string, validator=validators.instance_of(str))
    tracks: tuple[Track, ...] = field(default=(), 
                                      converter=_convert_track_tuple, 
                                      validator=validators.deep_iterable(
                                          member_validator=validators.instance_of(Track), 
                                          iterable_validator=validators.instance_of(tuple)))
    links: tuple[str, ...] = field(default=(), 
                                   converter=_convert_string_tuple,
                                   validator=validators.deep_iterable(
                                       member_validator=validators.instance_of(str), 
                                       iterable_validator=validators.instance_of(tuple)))

