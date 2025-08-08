import json
import os
from collections import defaultdict
from enum import IntEnum, IntFlag, auto
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import (FileSystemEventHandler, DirMovedEvent, FileMovedEvent, DirCreatedEvent, 
    FileCreatedEvent, DirDeletedEvent, FileDeletedEvent, DirModifiedEvent, FileModifiedEvent)

from src.logger import logger_watched
from src.common.json_encoder import CustomJSONEncoder
from src.ongaku_library.basemodels import Album, Track
from src.common.utils import legalize_filename


ALBUM_FILENAME = "[{catalognumber}] [{date}] {album} [{trackcounts}]"
TRACK_FILENAME = "{tracknumber}. {title}"


AUDIO_EXTS = {".mp3", ".flac"}
IMG_EXTS = {".jpg", ".png"}


class ResourceState(IntEnum):
    """专辑资源状态"""
    LOSSLESS = 2
    LOSSY = 1
    MISSING = 0


class MetadataState(IntFlag):
    """专辑元数据文件状态"""
    TITLE_EXIST = auto()
    DATE_EXIST = auto()
    CATNO_EXIST = auto()
    TRACK_EXIST = auto()
    ARTIST_EXIST = auto()
    COVER_EXIST = auto()


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


def dump_album_model(album: Album, filepath: str) -> None:
    album.links = list(set(album.links))
    album.themes = list(set(album.themes))
    _dict = album.model_dump()
    _dict["tracks"] = [[t.tracknumber, t.title, t.artist] for t in album.tracks]
    Path(filepath).write_text(json.dumps(_dict, ensure_ascii=False, indent=4, cls=CustomJSONEncoder), encoding="utf-8")


def load_album_model(filepath: str) -> Album:
    _dict: dict = json.loads(Path(filepath).read_text(encoding="utf-8"))
    _dict["tracks"] = [Track(tracknumber=l[0], title=l[1], artist=l[2]) for l in _dict["tracks"]]
    album = Album(**_dict)
    return album


class MyHandler(FileSystemEventHandler):

    def on_moved(self, event: DirMovedEvent | FileMovedEvent) -> None:
        pass

    def on_created(self, event: DirCreatedEvent | FileCreatedEvent) -> None:
        pass

    def on_deleted(self, event: DirDeletedEvent | FileDeletedEvent) -> None:
        pass

    def on_modified(self, event: DirModifiedEvent | FileModifiedEvent) -> None:
        pass


class OngakuLibrary:

    def __init__(self, metadata_dir: str, resource_dir: str) -> None:
        self.metadata_dir = metadata_dir
        self.resource_dir = resource_dir

        # 内部动态属性
        self._albums: list[Album] = []
        self._aid2n: dict[int, int] = {}

        self._mdfs: list[str] = []
        self._res_dirs: list[str] = []
        self._covers: list[str] = []
        self._metadata_states: list[MetadataState] = []
        self._resource_states: list[ResourceState] = []
        self._track_states: list[list[ResourceState]] = []
        self._theme_completions: dict[str, float] = {}

        self._scan()

    def get_albums(self) -> list[Album]:
        return self._albums

    def get_album_metadata_files(self, a: Album = None) -> str | list[str]:
        return self._mdfs[self._aid2n[id(a)]] if a else self._mdfs

    def get_album_resource_dirs(self, a: Album = None) -> str | list[str]:
        return self._res_dirs[self._aid2n[id(a)]] if a else self._res_dirs

    def get_album_covers(self, a: Album = None) -> str | list[str]:
        return self._covers[self._aid2n[id(a)]] if a else self._covers

    def get_album_metadata_states(self, a: Album = None) -> MetadataState | list[MetadataState]:
        return self._metadata_states[self._aid2n[id(a)]] if a else self._metadata_states

    def get_album_resource_states(self, a: Album = None) -> ResourceState | list[ResourceState]:
        return self._resource_states[self._aid2n[id(a)]] if a else self._resource_states

    def get_album_track_states(self, a: Album = None) -> list[ResourceState] | list[list[ResourceState]]:
        return self._track_states[self._aid2n[id(a)]] if a else self._track_states
    
    def get_theme_completions(self, t: str = None) -> float | dict[str, float]:
        return self._theme_completions.get(t, 0) if t else self._theme_completions
    
    def get_album_dst_resource_dirs(self, a: Album = None) -> str | list[str]:
        if a:
            # 相同目录结构
            rel_path = os.path.relpath(self.get_album_metadata_files(a), self.metadata_dir)
            rel_path = os.path.splitext(rel_path)[0]
            dst = os.path.join(self.resource_dir, rel_path)
            return dst

        dsts = [os.path.join(self.resource_dir, os.path.splitext(os.path.relpath(mdf, self.metadata_dir))[0]) 
                for mdf in self._mdfs]
        return dsts

    # 内部方法

    @logger_watched(1)
    def _scan(self) -> None:
        self._mdfs = list(map(str, Path(self.metadata_dir).rglob("*.json")))
        self._albums = list(map(load_album_model, self._mdfs))
        self._aid2n = {id(a): i for i, a in enumerate(self._albums)}

        _dname2path = {p.name: p for p in Path(self.resource_dir).rglob("*") if p.is_dir()}
        # 专辑资源目录 与 专辑元数据文件 同名
        self._res_dirs = [str(_dname2path.get(os.path.splitext(os.path.basename(f))[0], "")) for f in self._mdfs]

        self._resource_states, self._track_states = zip(*[self._scan_resource_state(a, d) for a, d in zip(self._albums, self._res_dirs)])

        self._covers = [None if not d else next((str(p) for p in Path(d).rglob("cover.*") if p.suffix.lower() in IMG_EXTS), None) 
                        for d in self._res_dirs]
        
        self._metadata_states = [self._scan_metadata_state(a, c) for a, c in zip(self._albums, self._covers)]

        self._theme_completions = self._count_theme_completions(self._albums, self._resource_states)

    @staticmethod
    def _scan_resource_state(album: Album, res_dir: str) -> tuple[ResourceState, list[ResourceState]]:
        # 无 track 信息时为 MISSING
        if not album.tracks:
            return ResourceState.MISSING, []
        
        if not res_dir:
            return ResourceState.MISSING, [ResourceState.MISSING]*len(album.tracks)
        
        name2ext = {p.stem: p.suffix for p in Path(res_dir).iterdir()}
        _map = {"": ResourceState.MISSING, ".mp3": ResourceState.LOSSY, ".flac": ResourceState.LOSSLESS}
        t_states = [_map[name2ext.get(n, "")] for n in track_filenames(album)]
        a_state = min(t_states)

        return a_state, t_states
    
    @staticmethod
    def _scan_metadata_state(album: Album, cover: str) -> MetadataState:
        state = MetadataState(0)
        
        if album.album:
            state |= MetadataState.TITLE_EXIST
        if album.date:
            state |= MetadataState.DATE_EXIST
        if album.catalognumber:
            state |= MetadataState.CATNO_EXIST
        if album.tracks:
            state |= MetadataState.TRACK_EXIST
            if all(t.artist for t in album.tracks):
                state |= MetadataState.ARTIST_EXIST
        if cover:
            state |= MetadataState.COVER_EXIST
        
        return state
    
    @staticmethod
    def _count_theme_completions(albums: list[Album], resource_states: list[ResourceState]) -> dict[str, float]:
        total, missing = defaultdict(int), defaultdict(int)
        for a, s in zip(albums, resource_states):
            for t in a.themes:
                total[t] += 1
                missing[t] += s == ResourceState.MISSING
        completions = {k: (v - missing.get(k, 0)) / v for k, v in total.items()}
        return completions
