import os
from enum import IntEnum, IntFlag, auto
from pathlib import Path

from src.logger import logger, logger_watched
from src.basemodels import Album, Track
from src.utils import legalize_filename
from src.repository_utils import load_albums_from_toml, album_filename, track_filenames


AUDIO_EXTS = {".mp3", ".flac"}
IMG_EXTS = {".jpg", ".png"}


class ResourceState(IntEnum):
    """
    专辑资源状态
    """
    LOSSLESS = 2
    LOSSY = 1
    MISSING = 0


class MetadataState(IntFlag):
    """
    专辑元数据文件状态
    """
    TITLE_EXIST = auto()
    DATE_EXIST = auto()
    CATNO_EXIST = auto()
    TRACK_EXIST = auto()
    ARTIST_EXIST = auto()
    COVER_EXIST = auto()


class ThemeKanBan:

    def __init__(self, theme_metadata_file: str, theme_directory: str = None) -> None:
        self.theme_metadata_file = theme_metadata_file
        self.theme_directory = theme_directory

        self.theme_name = Path(self.theme_metadata_file).stem
        self.theme_completion: float = None

        self.albums: list[Album] = None
        self.res_dirs: list[str] = None
        self.covers: list[str | None] = None
        self.metadata_states: list[MetadataState] = None
        self.resource_states: list[ResourceState] = None
        self.track_states: list[list[ResourceState]] = None
        
        # 缓存
        self._aid2n: dict[int, int] = None

        self.scan_all()

    def get_album_res_dir(self, a: Album) -> str:
        return self.res_dirs[self._aid2n[id(a)]]

    def get_album_cover(self, a: Album) -> str | None:
        return self.covers[self._aid2n[id(a)]]

    def get_album_metadata_state(self, a: Album) -> MetadataState:
        return self.metadata_states[self._aid2n[id(a)]]

    def get_album_resource_state(self, a: Album) -> ResourceState:
        return self.resource_states[self._aid2n[id(a)]]

    def get_album_track_states(self, a: Album) -> list[ResourceState]:
        return self.track_states[self._aid2n[id(a)]]

    def scan_all(self) -> None:
        self.albums = load_albums_from_toml(self.theme_metadata_file)
        self._aid2n = {id(a): i for i, a in enumerate(self.albums)}

        self.res_dirs = [os.path.join(self.theme_directory, legalize_filename(album_filename(a))) for a in self.albums]

        self.resource_states, self.track_states = zip(*[self._scan_resource_state(a, d) for a, d in zip(self.albums, self.res_dirs)])

        self.covers = [None if not os.path.exists(d) else 
                       next((str(p) for p in Path(d).rglob("cover.*") if p.suffix.lower() in IMG_EXTS), None) 
                       for d in self.res_dirs]
        
        self.metadata_states = [self._scan_metadata_state(a, c) for a, c in zip(self.albums, self.covers)]

        self.theme_completion = sum(map(os.path.exists, self.res_dirs)) / len(self.albums)

    # 内部方法

    @staticmethod
    def _scan_resource_state(album: Album, res_dir: str) -> tuple[ResourceState, list[ResourceState]]:
        # 无 track 信息时为 MISSING
        if not album.tracks:
            return ResourceState.MISSING, []
        
        if not os.path.exists(res_dir):
            return ResourceState.MISSING, [ResourceState.MISSING]*len(album.tracks)
        
        name2ext = {p.stem: p.suffix for p in Path(res_dir).iterdir()}
        _map = {"": ResourceState.MISSING, ".mp3": ResourceState.LOSSY, ".flac": ResourceState.LOSSLESS}
        t_states = [_map[name2ext.get(n, "")] for n in track_filenames(album)]
        a_state = min(t_states)

        return a_state, t_states
    
    @staticmethod
    def _scan_metadata_state(album: Album, cover: str | None) -> MetadataState:
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


class KanBan:

    def __init__(self, metadata_dir: str, resource_dir: str = None) -> None:
        self.metadata_dir = metadata_dir
        self.resource_dir = resource_dir

        self.theme_kanbans: list[ThemeKanBan] = None

        self._theme2kanban: dict[str, ThemeKanBan] = None

        self.scan_all()

    def get_theme_kanban(self, theme: str) -> ThemeKanBan | None:
        return self._theme2kanban.get(theme)

    @logger_watched(1)
    def scan_all(self) -> None:

        theme_mdfs = list(Path(self.metadata_dir).glob("*.toml"))
        theme_dirs = [os.path.join(self.resource_dir, f.stem) for f in theme_mdfs]

        self.theme_kanbans = [ThemeKanBan(f, d) for f, d in zip(theme_mdfs, theme_dirs)]

        self._theme2kanban = {t.theme_name: t for t in self.theme_kanbans}
