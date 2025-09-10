"""
定义专辑元数据的数据模型
基本元数据：
catalognumber, date, album, tracknumber, title, artist
自定义元数据：
links
"""

from typing import Any, Annotated, Iterable, Optional

from pydantic import BaseModel, Field, BeforeValidator, field_validator


def _validate_int(value: Any) -> int:
    """
    1. 转换 None 为 0
    """
    if value is None:
        value = 0
    if not isinstance(value, int):
        raise ValueError(f"value is not int: {value}")
    return value


def _validate_string(value: Any) -> str:
    """
    1. 转换 None 为空字符串
    2. 去除首尾空字符
    """
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValueError(f"value is not str: {value}")
    return value.strip()


def _validate_strtuple(value: Any) -> tuple:
    """
    1. do_string
    2. 元组排序、去重
    """
    if not isinstance(value, Iterable) or isinstance(value, str):
        raise ValueError(f"value is not iterable: {value}")
    value = tuple(sorted(set(map(_validate_string, value))))
    return value


def _validate_tracks_field(tracks: tuple["Track"]) -> tuple["Track"]:
    """
    1. 列表转元组
    2. 按照 tracknumber 排序
    """
    tracks = tuple(sorted(tracks, key=lambda t: t.tracknumber))
    return tracks


_CustomInt = Annotated[int, BeforeValidator(_validate_int)]
_CustomStr = Annotated[str, BeforeValidator(_validate_string)]
_CustomStrTuple = Annotated[tuple[str, ...], BeforeValidator(_validate_strtuple)]


class Album(BaseModel, validate_assignment=True):
    """
    :param date: 仅允许四种模式： ["", "2005", "2005-01", "2005-01-01"]
    """
    catalognumber: _CustomStr = Field(default="")
    date: _CustomStr = Field(default="", pattern=r"^$|^\d{4}$|^\d{4}-\d{1,2}$|^\d{4}-\d{1,2}-\d{1,2}$")
    album: _CustomStr = Field(default="")
    tracks: tuple["Track", ...] = Field(default_factory=tuple)
    links: _CustomStrTuple = Field(default_factory=tuple)

    _validate_tracks = field_validator("tracks", mode="after")(_validate_tracks_field)

    def __hash__(self) -> int:
        return hash((self.catalognumber, self.date, self.album, self.tracks, self.links))


class Disc(BaseModel, validate_assignment=True):
    discnumber: _CustomInt = Field(default=0)
    disc: _CustomStr = Field(default="")
    tracks: tuple["Track", ...] = Field(default_factory=tuple)

    _validate_tracks = field_validator("tracks", mode="after")(_validate_tracks_field)

    def __hash__(self) -> int:
        return hash((self.discnumber, self.disc, self.tracks))


class Track(BaseModel, validate_assignment=True):
    tracknumber: _CustomInt = Field(default=0)
    title: _CustomStr = Field(default="")
    artist: _CustomStr = Field(default="")
    mark: _CustomStr = Field(default="")

    def __hash__(self) -> int:
        return hash((self.tracknumber, self.title, self.artist))

