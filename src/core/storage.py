"""
定义元数据持久化格式，资源存储路径规则
"""

from pathlib import Path

import rtoml
from attrs import asdict
from cattrs import Converter

from src.core.basemodels import Album, TrackMark
from src.utils import legalize_filename, dump_toml


# 专辑文件名主干
ALBUM_STEMNAME = "[{catalognumber}] [{date}] {album} [{trackcounts}]"
# 音轨文件名主干
TRACK_STEMNAME = "{tracknumber}. {title}"
# 封面文件名
COVER_NAME = "cover.png"

def album_stemname(album: Album) -> str:
    """
    专辑文件名主干。
    缺失的字段将会以 None 填充。
    """
    name = ALBUM_STEMNAME.format(catalognumber=album.catalognumber, date=album.date, 
                                 album=album.album, trackcounts=len(album.tracks))
    name = legalize_filename(name)
    return name


def track_stemnames(album: Album) -> list[str]:
    """
    专辑的音轨文件名主干列表。
    """
    digit_length = len(str(len(album.tracks)))
    names = [f"{str(i+1).zfill(digit_length)}. {t.title}" for i, t in enumerate(album.tracks)]
    names = list(map(legalize_filename, names))
    return names


def dump_albums_to_toml(albums: list[Album], filepath: str) -> None:
    """
    将 Album 模型列表 序列化为 TOML 格式 并保存到文件。

    1. 按照 Album.date 升序
    """
    ds = list(map(asdict, sorted(albums, key=lambda a: a.date)))
    for d in ds:
        d["tracks"] = [[t["tracknumber"], t["title"], t["artist"], t["mark"]] for t in d["tracks"]]
    obj = {str(i+1): d for i, d in enumerate(ds)}
    dump_toml(obj, filepath)


def load_albums_from_toml(filepath: str) -> list[Album]:
    """
    从 TOML 文件 解析 Album 模型列表。
    """
    text = Path(filepath).read_text(encoding="utf-8")
    if not text:
        return []
    obj = rtoml.loads(text)
    ds = obj.values()
    for d in ds:
        # 适配 artist mark 字段省略
        for t in d["tracks"]:
            if len(t) == 2: t.append("")
            if len(t) == 3: t.append(TrackMark.UNKNOWN)
        d["tracks"] = [{"tracknumber": t[0], "title": t[1], "artist": t[2], "mark": t[3]} 
                       for t in d["tracks"]]
    converter = Converter()
    albums = [converter.structure(d, Album) for d in ds]
    return albums


