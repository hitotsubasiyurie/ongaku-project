import os
from pathlib import Path
from typing import Callable
from dataclasses import dataclass, field
from enum import IntEnum, IntFlag, auto

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


@dataclass
class AlbumKanBan:
    """
    :param album: 专辑模型
    :param album_dir: 专辑目录路径

    :var cover: 封面路径
    :var metadata_state: 专辑元数据状态

    :var track_files: 音轨文件路径列表
    :var track_stat_results: 音轨文件属性列表

    :var resource_state: 专辑资源状态
    :var track_states: 专辑轨道资源状态列表
    """

    album: Album
    album_dir: str

    cover: str = field(init=False)
    metadata_state: MetadataState = field(init=False)

    track_files: list[str] = field(init=False)
    track_stat_results: list[os.stat_result] = field(init=False)

    album_res_state: ResourceState = field(init=False)
    track_res_states: list[ResourceState] = field(init=False)

    def __post_init__(self) -> None:
        self._analyze_resource()
        self._analyze_metadata()

    def _analyze_metadata(self) -> None:
        is_img: Callable[[Path], bool] = lambda p: p.suffix.lower() in IMG_EXTS

        if os.path.exists(self.album_dir):
            self.cover = next((map(str, filter(is_img, Path(self.album_dir).rglob("cover.*")))), "")
        else:
            self.cover = ""

        self.metadata_state = MetadataState(0)
        
        if self.album.album:
            self.metadata_state |= MetadataState.TITLE_EXIST
        if self.album.date:
            self.metadata_state |= MetadataState.DATE_EXIST
        if self.album.catalognumber:
            self.metadata_state |= MetadataState.CATNO_EXIST
        if self.album.tracks:
            self.metadata_state |= MetadataState.TRACK_EXIST
            if all(t.artist for t in self.album.tracks):
                self.metadata_state |= MetadataState.ARTIST_EXIST
        if self.album:
            self.metadata_state |= MetadataState.COVER_EXIST

    def _analyze_resource(self) -> None:
        if not self.album.tracks or not os.path.exists(self.album_dir):
            self.album_res_state = ResourceState.MISSING
            _len = len(self.album.tracks)
            self.track_files, self.track_stat_results, self.track_res_states = [""] * _len, [None] * _len, [None] * _len
            return

        stem2ext = {p.stem: p.suffix for p in Path(self.album_dir).iterdir()}

        self.track_files = [os.path.join(self.album_dir, n+stem2ext[n]) if n in stem2ext else "" 
                            for n in track_filenames(self.album)]
        self.track_stat_results = [os.stat(f) if f else None for f in self.track_files]

        _map = {"": ResourceState.MISSING, ".mp3": ResourceState.LOSSY, ".flac": ResourceState.LOSSLESS}
        self.track_res_states = [_map[stem2ext.get(n, "")] for n in track_filenames(self.album)]
        self.album_res_state = min(self.track_res_states)


@dataclass
class ThemeKanBan:
    """
    :param theme_metadata_file: 主题元数据文件
    :param theme_directory: 主题资源目录

    :var theme_name: 主题名
    :var collection_progress: 资源收集进度
    :var marking_progress: 标记进度

    :var album_kanbans: 
    """

    theme_metadata_file: Path
    theme_directory: Path

    theme_name: str = field(init=False)
    collection_progress: float = field(init=False)
    marking_progress: float = field(init=False)

    album_kanbans: list[AlbumKanBan] = field(init=False)

    def __post_init__(self) -> None:
        self.scan()

    @logger_watched(1)
    def scan(self) -> None:
        self.theme_name = Path(self.theme_metadata_file).stem

        albums = load_albums_from_toml(self.theme_metadata_file)
        album_dirs = [os.path.join(self.theme_directory, legalize_filename(album_filename(a))) for a in albums]
        self.album_kanbans = [AlbumKanBan(a, d) for a, d in zip(albums, album_dirs)]

        if albums:
            self.marking_progress = sum(bool(a.mark) for a in albums) / len(albums)
            self.collection_progress = sum(k.album_res_state != ResourceState.MISSING for k in self.album_kanbans) / len(albums)
        else:
            self.marking_progress = 0
            self.collection_progress = 0


@dataclass
class KanBan:
    """
    :param metadata_dir: 元数据目录
    :param resource_dir: 资源目录

    :var theme_kanbans: 
    """

    metadata_dir: str
    resource_dir: str

    theme_kanbans: list[ThemeKanBan] = field(init=False)

    # 缓存
    _theme2kanban: dict[str, ThemeKanBan] = field(init=False)

    def __post_init__(self) -> None:
        self.scan()

    def get_theme_kanban(self, theme: str) -> ThemeKanBan | None:
        return self._theme2kanban.get(theme)

    @logger_watched(2)
    def scan(self) -> None:
        theme_mdfs = list(Path(self.metadata_dir).glob("*.toml"))
        theme_dirs = [os.path.join(self.resource_dir, f.stem) for f in theme_mdfs]

        self.theme_kanbans = [ThemeKanBan(f, d) for f, d in zip(theme_mdfs, theme_dirs)]

        self._theme2kanban = {t.theme_name: t for t in self.theme_kanbans}


