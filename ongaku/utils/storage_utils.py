from pathlib import Path

import rtoml

from ongaku.core.basemodels import Album
from ongaku.utils.utils import legalize_filename, dump_toml


ALBUM_FILENAME = "[{catalognumber}] [{date}] {album} [{trackcounts}]"
TRACK_FILENAME = "{tracknumber}. {title}"


def album_filename(album: Album) -> str:
    """
    专辑文件名。
    """
    name = ALBUM_FILENAME.format(catalognumber=album.catalognumber, date=album.date, 
                                 album=album.album, trackcounts=len(album.tracks))
    name = legalize_filename(name)
    return name


def track_filenames(album: Album) -> list[str]:
    """
    专辑的音轨文件名列表。
    """
    digit_length = len(str(len(album.tracks)))
    names = [f"{str(i+1).zfill(digit_length)}. {t.title}" for i, t in enumerate(album.tracks)]
    names = list(map(legalize_filename, names))
    return names


def dump_albums_to_toml(albums: list[Album], filepath: str) -> None:
    """
    将 Album 模型列表 序列化为 TOML 格式 并保存到文件。
    """
    ds = list(map(Album.model_dump, albums))
    for d in ds:
        d["tracks"] = [[t["tracknumber"], t["title"], t["artist"], t["mark"]] for t in d["tracks"]]
    obj = {str(i+1): d for i, d in enumerate(ds)}
    dump_toml(obj, filepath)


def load_albums_from_toml(filepath: str) -> list[Album]:
    """
    从 TOML 文件 重建 Album 模型列表。
    """
    text = Path(filepath).read_text(encoding="utf-8")
    if not text:
        return []
    obj = rtoml.load(text)
    ds = obj.values()
    for d in ds:
        d["tracks"] = [{"tracknumber": t[0], "title": t[1], "artist": t[2], "mark": t[3] if len(t) > 3 else ""} for t in d["tracks"]]
    albums = [Album(**d) for d in ds]
    return albums

