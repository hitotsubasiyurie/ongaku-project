import os
from pathlib import Path
from typing import Callable
from dataclasses import dataclass, field
from enum import IntEnum, IntFlag, auto
from concurrent.futures import ThreadPoolExecutor

from ongaku.core.logger import logger_watched
from ongaku.core.basemodels import Album
from ongaku.core.constants import IMG_EXTS
from ongaku.utils.utils import legalize_filename
from ongaku.utils.storage_utils import load_albums_from_toml, album_filename, track_filenames, dump_albums_to_toml


class ResourceState(IntEnum):
    """
    专辑资源状态
    """
    # 完整无损
    LOSSLESS = 3
    # 完整有损
    LOSSY = 2
    # 不完整
    PARTIAL = 1
    # 缺失
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

    track_files: tuple[str, ...] = field(init=False)
    track_stat_results: tuple[os.stat_result, ...] = field(init=False)

    album_res_state: ResourceState = field(init=False)
    track_res_states: tuple[ResourceState, ...] = field(init=False)

    def __post_init__(self) -> None:
        self.scan()
        self.count_state()

    def scan(self) -> None:
        """
        扫描文件系统。
        """
        # album_dir 不存在时
        if not os.path.exists(self.album_dir):
            self.cover = ""
            _len = len(self.album.tracks)
            self.track_files = ("",) * _len
            self.track_stat_results = (None,) * _len
            return
        
        is_img: Callable[[Path], bool] = lambda p: p.suffix.lower() in IMG_EXTS
        self.cover = next((map(str, filter(is_img, Path(self.album_dir).rglob("cover.*")))), "")

        stem2ext = {p.stem: p.suffix for p in Path(self.album_dir).iterdir()}

        # 例如 [path1, "", "", path4, ...]
        self.track_files = tuple(os.path.join(self.album_dir, n+stem2ext[n]) if n in stem2ext else "" 
                                 for n in track_filenames(self.album))
        self.track_stat_results = tuple(os.stat(f) if f else None for f in self.track_files)

    def count_state(self) -> None:
        self.metadata_state = MetadataState(0)
        
        if self.album.album:
            self.metadata_state |= MetadataState.TITLE_EXIST
        if self.album.date:
            self.metadata_state |= MetadataState.DATE_EXIST
        if self.album.catalognumber:
            self.metadata_state |= MetadataState.CATNO_EXIST
        if self.album.tracks:
            self.metadata_state |= MetadataState.TRACK_EXIST
            # 任一 track 有 artist 信息 
            if any(t.artist for t in self.album.tracks):
                self.metadata_state |= MetadataState.ARTIST_EXIST
        if self.cover:
            self.metadata_state |= MetadataState.COVER_EXIST

        _map = {"": ResourceState.MISSING, ".mp3": ResourceState.LOSSY, ".flac": ResourceState.LOSSLESS}
        self.track_res_states = tuple(_map[Path(f).suffix.lower() if f else ""] for f in self.track_files)
        
        # 无 tracks 元数据时为 MISSING
        if not self.album.tracks:
            self.album_res_state = ResourceState.MISSING
        elif all(self.track_res_states):
            self.album_res_state = min(self.track_res_states)
        elif any(self.track_res_states):
            self.album_res_state = ResourceState.PARTIAL
        else:
            self.album_res_state = ResourceState.MISSING

    def __hash__(self) -> int:
        return hash((self.album, self.album_dir, 
                     self.cover, self.metadata_state, self.track_files,
                     self.track_stat_results, self.album_res_state, self.track_res_states))


@dataclass
class ThemeKanBan:
    """
    :param theme_metadata_file: 主题元数据文件
    :param theme_directory: 主题资源目录

    :var theme_name: 主题名
    :var collection_progress: 资源收集进度
    :var mark_progress: 标记进度

    :var album_kanbans: 
    """

    theme_metadata_file: Path
    theme_directory: Path

    theme_name: str = field(init=False)
    collection_progress: float = field(init=False)
    mark_progress: float = field(init=False)

    album_kanbans: tuple[AlbumKanBan, ...] = field(init=False)

    def __post_init__(self) -> None:
        self.scan()
        self.count_progress()

    def scan(self) -> None:
        """
        扫描文件系统。
        """
        self.theme_name = Path(self.theme_metadata_file).stem

        albums = load_albums_from_toml(self.theme_metadata_file)
        album_dirs = [os.path.join(self.theme_directory, legalize_filename(album_filename(a))) for a in albums]
        self.album_kanbans = tuple(AlbumKanBan(a, d) for a, d in zip(albums, album_dirs))

    def count_progress(self) -> None:
        albums = [k.album for k in self.album_kanbans]
        if albums:
            self.mark_progress = sum(bool(t.mark) for a in albums for t in a.tracks) / sum(len(a.tracks) for a in albums)
            self.collection_progress = sum(k.album_res_state != ResourceState.MISSING for k in self.album_kanbans) / len(albums)
        else:
            self.mark_progress = 0
            self.collection_progress = 0

    def save_metadata_file(self) -> None:
        albums = [k.album for k in self.album_kanbans]
        dump_albums_to_toml(albums, self.theme_metadata_file)

    def __hash__(self) -> int:
        return hash((self.theme_metadata_file, self.theme_directory, self.theme_name, 
                     self.collection_progress, self.mark_progress, self.album_kanbans))

@dataclass
class KanBan:
    """
    :param metadata_dir: 元数据目录
    :param resource_dir: 资源目录

    :var theme_kanbans: 
    """

    metadata_dir: str
    resource_dir: str

    theme_kanbans: tuple[ThemeKanBan, ...] = field(init=False)

    # 缓存
    _theme2kanban: dict[str, ThemeKanBan] = field(init=False)

    def __post_init__(self) -> None:
        self.scan()

    def get_theme_kanban(self, theme: str) -> ThemeKanBan | None:
        return self._theme2kanban.get(theme)

    @logger_watched(2)
    def scan(self) -> None:
        """
        扫描文件系统。
        """
        theme_mdfs = tuple(Path(self.metadata_dir).glob("*.toml"))
        theme_dirs = [os.path.join(self.resource_dir, f.stem) for f in theme_mdfs]

        with ThreadPoolExecutor() as executor:
            self.theme_kanbans = tuple(executor.map(ThemeKanBan, theme_mdfs, theme_dirs))

        self._theme2kanban = {t.theme_name: t for t in self.theme_kanbans}

    def __hash__(self) -> int:
        return hash((self.metadata_dir, self.resource_dir, self.theme_kanbans))
