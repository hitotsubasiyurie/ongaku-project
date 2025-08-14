"""
定义专辑基本元数据的数据结构
对应的元数据标签为：
catalognumber, date, album, tracknumber, title, artist
themes, links
"""

from pydantic import BaseModel, Field


class Album(BaseModel):
    catalognumber: str = Field(default="")
    date: str = Field(default="")
    album: str = Field(default="")
    tracks: list["Track"] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)


class Disc(BaseModel):
    discnumber: int | None = Field(default=None)
    disc: str = Field(default="")
    tracks: list["Track"] = Field(default_factory=list)


class Track(BaseModel):
    tracknumber: int | None = Field(default=None)
    title: str = Field(default="")
    artist: str = Field(default="")


