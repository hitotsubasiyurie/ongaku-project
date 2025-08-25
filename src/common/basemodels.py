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


def _validate_strlist(value: Any) -> list:
    """
    1. do_string
    2. 列表排序、去重
    """
    if not isinstance(value, Iterable) or isinstance(value, str):
        raise ValueError(f"value is not iterable: {value}")
    value = list(sorted(set(map(_validate_string, value))))
    return value


def _validate_tracks_field(tracks: list["Track"]) -> list["Track"]:
    """
    2. 按照 tracknumber 排序
    """
    tracks = list(sorted(tracks, key=lambda t: t.tracknumber))
    return tracks


_CustomInt = Annotated[int, BeforeValidator(_validate_int)]
_CustomStr = Annotated[str, BeforeValidator(_validate_string)]
_CustomStrList = Annotated[list[str], BeforeValidator(_validate_strlist)]


class Album(BaseModel):
    """
    :param date: 仅允许四种模式： ["", "2005", "2005-01", "2005-01-01"]
    """
    catalognumber: _CustomStr = Field(default="")
    date: _CustomStr = Field(default="", pattern=r"^$|^\d{4}$|^\d{4}-\d{1,2}$|^\d{4}-\d{1,2}-\d{1,2}$")
    album: _CustomStr = Field(default="")
    tracks: list["Track"] = Field(default_factory=list)
    links: _CustomStrList = Field(default_factory=list)

    _validate_tracks = field_validator("tracks", mode="after")(_validate_tracks_field)


class Disc(BaseModel):
    discnumber: _CustomInt = Field(default=0)
    disc: _CustomStr = Field(default="")
    tracks: list["Track"] = Field(default_factory=list)

    _validate_tracks = field_validator("tracks", mode="after")(_validate_tracks_field)


class Track(BaseModel):
    tracknumber: _CustomInt = Field(default=0)
    title: _CustomStr = Field(default="")
    artist: _CustomStr = Field(default="")

