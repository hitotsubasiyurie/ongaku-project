"""
定义专辑元数据的数据模型
基本元数据：
catalognumber, date, album, tracknumber, title, artist
自定义元数据：
themes, links
"""

from typing import Any, Annotated, Iterable, Optional

from pydantic import BaseModel, Field, BeforeValidator, field_validator


def _do_string(value: Any) -> str:
    """
    1. 转换 None 为空字符串
    2. 去除首尾空字符
    """
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValueError(f"value is not str: {value}")
    return value.strip()


def _do_strlist(value: Any) -> list:
    """
    1. do_string
    2. 列表去重
    """
    if not isinstance(value, Iterable) or isinstance(value, str):
        raise ValueError(f"value is not iterable: {value}")
    value = list(set(map(_do_string, value)))
    return value


def _do_tracks_field(tracks: list["Track"]) -> list["Track"]:
    """
    1. 列表去重
    2. 按照 tracknumber 排序
    """
    tracks = list(sorted(set(tracks), key=lambda t: t.tracknumber or float("inf")))
    return tracks


_CustomStr = Annotated[str, BeforeValidator(_do_string)]
_CustomStrList = Annotated[list[str], BeforeValidator(_do_strlist)]


class Album(BaseModel):
    """
    :param date: 仅允许四种模式： ["", "2005", "2005-01", "2005-01-01"]
    """
    catalognumber: _CustomStr = Field(default="")
    date: _CustomStr = Field(default="", pattern=r"^$|^\d{4}$|^\d{4}-\d{1,2}$|^\d{4}-\d{1,2}-\d{1,2}$")
    album: _CustomStr = Field(default="")
    tracks: list["Track"] = Field(default_factory=list)
    themes: _CustomStrList = Field(default_factory=list)
    links: _CustomStrList = Field(default_factory=list)

    _validate_tracks = field_validator("tracks", mode="after")(_do_tracks_field)


class Disc(BaseModel):
    discnumber: Optional[int] = Field(default=None)
    disc: _CustomStr = Field(default="")
    tracks: list["Track"] = Field(default_factory=list)

    _validate_tracks = field_validator("tracks", mode="after")(_do_tracks_field)


class Track(BaseModel):
    tracknumber: Optional[int] = Field(default=None)
    title: _CustomStr = Field(default="")
    artist: _CustomStr = Field(default="")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Track):
            return NotImplemented
        return (self.tracknumber, self.title, self.artist) == (other.tracknumber, other.title, other.artist)

    def __hash__(self) -> int:
        return hash((self.tracknumber, self.title, self.artist))


def dump_album(a: Album) -> dict[str, Any]:
    value = {
        "catalognumber": a.catalognumber,
        "date": a.date,
        "album": a.album,
        "tracks": [(t.tracknumber, t.title, t.artist) for t in a.tracks]
    }
    return value


def construct_album(value: dict[str, Any]) -> Album:
    tracks=[Track(tracknumber=t[0], title=t[1], artist=t[2]) 
            for t in value.get("tracks", [])]
    album = Album(catalognumber=value.get("catalognumber"), date=value.get("date"), 
                  album=value.get("album"), tracks=tracks)
    return album

