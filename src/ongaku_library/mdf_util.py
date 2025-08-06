import json
import os
from enum import Enum
from pathlib import Path

from src.common.json_encoder import CustomJSONEncoder
from src.ongaku_library.basemodels import Album, Track
from src.common.utils import legalize_filename

ALBUM_FILENAME = "[{catalognumber}] [{date}] {album} [{trackcounts}]"
TRACK_FILENAME = "{tracknumber}. {title}"


def album_filename(album: Album) -> str:
    name = ALBUM_FILENAME.format(catalognumber=album.catalognumber, date=album.date, 
                                 album=album.album, trackcounts=len(album.tracks))
    name = legalize_filename(name)
    return name


def track_filenames(album: Album) -> list[str]:
    digit_length = len(str(len(album.tracks)))
    names = [f"{str(i+1).zfill(digit_length)}. {t.title}" for i, t in enumerate(album.tracks)]
    names = list(map(legalize_filename, names))
    return names


def save_album(album: Album, filepath: str) -> None:
    album.links = list(set(album.links))
    album.themes = list(set(album.themes))
    _dict = album.model_dump()
    _dict["tracks"] = [[t.tracknumber, t.title, t.artist] for t in album.tracks]
    Path(filepath).write_text(json.dumps(_dict, ensure_ascii=False, indent=4, cls=CustomJSONEncoder), encoding="utf-8")


def load_album(filepath: str) -> Album:
    _dict: dict = json.loads(Path(filepath).read_text(encoding="utf-8"))
    _dict["tracks"] = [Track(tracknumber=l[0], title=l[1], artist=l[2]) for l in _dict["tracks"]]
    album = Album(**_dict)
    return album


class ResourceState(int, Enum):
    LOSSLESS = 0
    LOSSY = 1
    MISSING = 2


def get_album_state(album: Album, album_dir: str) -> ResourceState:
    if not album.tracks or not album_dir or not os.path.isdir(album_dir):
        return ResourceState.MISSING
    return _get_album_state(get_track_states(album, album_dir))


def _get_album_state(track_states: list[ResourceState]) -> ResourceState:
    track_states = set(track_states)
    if not track_states or ResourceState.MISSING in track_states:
        return ResourceState.MISSING
    if track_states == {ResourceState.LOSSLESS}:
        return ResourceState.LOSSLESS
    return ResourceState.LOSSY


def get_track_states(album: Album, album_dir: str) -> list[ResourceState]:
    if not album.tracks or not album_dir or not os.path.isdir(album_dir):
        return [ResourceState.MISSING] * len(album.tracks)
    
    name2ext = {p.stem: p.suffix for p in Path(album_dir).iterdir()}
    exts = [name2ext.get(n, "").lower() for n in track_filenames(album)]
    states = []
    for ext in exts:
        if ext == "":
            states.append(ResourceState.MISSING)
        elif ext == ".flac":
            states.append(ResourceState.LOSSLESS)
        else:
            states.append(ResourceState.LOSSY)

    return states




