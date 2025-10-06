import os
from pathlib import Path
from typing import Callable
from dataclasses import dataclass, field
from enum import IntEnum, IntFlag
from concurrent.futures import ThreadPoolExecutor
from functools import cached_property

import rtoml

from ongaku.core.logger import logger_watched
from ongaku.core.basemodels import Album
from ongaku.core.constants import IMG_EXTS
from ongaku.utils.utils import legalize_filename, dump_toml


ALBUM_FILENAME = "[{catalognumber}] [{date}] {album} [{trackcounts}]"
TRACK_FILENAME = "{tracknumber}. {title}"


def album_filename(album: Album) -> str:
    """
    专辑文件名。
    缺失的字段将会以 None 填充。
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
    obj = rtoml.loads(text)
    ds = obj.values()
    for d in ds:
        d["tracks"] = [{"tracknumber": t[0], "title": t[1], "artist": t[2], "mark": t[3] if len(t) > 3 else ""} for t in d["tracks"]]
    albums = [Album(**d) for d in ds]
    return albums


class ResourceState(IntEnum):
    """
    专辑资源状态
    """
    # 完整无损
    LOSSLESS = 3
    # 完整有损
    LOSSY    = 2
    # 不完整
    PARTIAL  = 1
    # 缺失
    MISSING  = 0


class MetadataState(IntFlag):
    """
    专辑元数据文件状态
    """
    NONE         = 0
    TITLE_EXIST  = 1 << 0
    DATE_EXIST   = 1 << 1
    CATNO_EXIST  = 1 << 2
    TRACK_EXIST  = 1 << 3
    ARTIST_EXIST = 1 << 4
    COVER_EXIST  = 1 << 5


@dataclass
class AlbumKanBan:
    """
    :param album: 专辑模型
    :param album_dir: 专辑目录路径

    :var cover: 封面路径
    :var track_files: 音轨文件路径列表。文件不存在时为 "" 。
    :var track_stat_results: 音轨文件属性列表

    :var metadata_state: 专辑元数据状态
    :var track_res_states: 专辑轨道资源状态列表
    :var album_res_state: 专辑资源状态
    """

    album: Album
    album_dir: str

    cover: str = field(init=False)
    track_files: tuple[str, ...] = field(init=False)
    track_stat_results: tuple[os.stat_result | None, ...] = field(init=False)

    def __post_init__(self) -> None:
        self.album_dir = os.path.abspath(self.album_dir)
        self.scan()

    def scan(self) -> None:
        """
        扫描文件系统。
        """
        # 专辑目录 不存在时
        if not os.path.exists(self.album_dir):
            self.cover = ""
            _len = len(self.album.tracks)
            self.track_files = ("",) * _len
            self.track_stat_results = (None,) * _len
            return
        
        # 专辑目录 必须是扁平的
        is_img: Callable[[Path], bool] = lambda p: p.suffix.lower() in IMG_EXTS
        self.cover = next(map(str, filter(is_img, Path(self.album_dir).glob("cover.*"))), "")

        stem2ext = {p.stem: p.suffix for p in Path(self.album_dir).iterdir()}

        self.track_files = tuple(os.path.join(self.album_dir, n+stem2ext[n]) if n in stem2ext else "" 
                                 for n in track_filenames(self.album))
        self.track_stat_results = tuple(os.stat(f) if f else None for f in self.track_files)

        # 失效属性缓存
        for attr in ("metadata_state", "track_res_states", "album_res_state"):
            self.__dict__.pop(attr, None)

    @cached_property
    def metadata_state(self) -> MetadataState:
        s = MetadataState.NONE
        
        if self.album.album:
            s |= MetadataState.TITLE_EXIST
        if self.album.date:
            s |= MetadataState.DATE_EXIST
        if self.album.catalognumber:
            s |= MetadataState.CATNO_EXIST
        if self.album.tracks:
            s |= MetadataState.TRACK_EXIST
            # 任一 track 有 artist 信息 
            if any(t.artist for t in self.album.tracks):
                s |= MetadataState.ARTIST_EXIST
        if self.cover:
            s |= MetadataState.COVER_EXIST

        return s

    @cached_property
    def track_res_states(self) -> tuple[ResourceState, ...]:
        _map = {"": ResourceState.MISSING, ".mp3": ResourceState.LOSSY, ".flac": ResourceState.LOSSLESS}
        states = tuple(_map[Path(f).suffix.lower() if f else ""] for f in self.track_files)
        return states
    
    @cached_property
    def album_res_state(self) -> ResourceState:
        # 无 tracks 元数据时为 MISSING
        if not self.album.tracks:
            s = ResourceState.MISSING
        elif all(self.track_res_states):
            s = min(self.track_res_states)
        elif any(self.track_res_states):
            s = ResourceState.PARTIAL
        else:
            s = ResourceState.MISSING

        return s

    def __hash__(self) -> int:
        return hash((self.album, self.album_dir, self.cover, self.track_files, self.track_stat_results))


@dataclass
class ThemeKanBan:
    """
    :param theme_metadata_file: 主题元数据文件路径
    :param theme_directory: 主题资源目录路径

    :var album_kanbans: 

    :var theme_name: 主题名
    :var collection_progress: 资源收集进度
    :var mark_progress: 标记进度
    """

    theme_metadata_file: str
    theme_directory: str

    album_kanbans: tuple[AlbumKanBan, ...] = field(init=False)

    def __post_init__(self) -> None:
        self.theme_metadata_file = os.path.abspath(self.theme_metadata_file)
        self.theme_directory = os.path.abspath(self.theme_directory)
        self.scan()

    def scan(self) -> None:
        """
        扫描文件系统。
        """
        albums = load_albums_from_toml(self.theme_metadata_file)
        # 主题资源目录 必须是扁平的
        album_dirs = [os.path.join(self.theme_directory, album_filename(a)) for a in albums]
        self.album_kanbans = tuple(AlbumKanBan(a, d) for a, d in zip(albums, album_dirs))

        # 失效属性缓存
        for attr in ("theme_name", "album_collection_progress", "track_mark_progress"):
            self.__dict__.pop(attr, None)

    @cached_property
    def theme_name(self) -> str:
        return Path(self.theme_metadata_file).stem

    @cached_property
    def album_collection_progress(self) -> float:
        albums = [k.album for k in self.album_kanbans]
        if albums:
            return sum(k.album_res_state != ResourceState.MISSING for k in self.album_kanbans) / len(albums)
        return 0

    @cached_property
    def track_mark_progress(self) -> float:
        albums = [k.album for k in self.album_kanbans]
        total = sum(len(a.tracks) for a in albums)
        if total:
            return sum(bool(t.mark) for a in albums for t in a.tracks) / total
        return 0

    def save_metadata_file(self) -> None:
        """
        保存元数据文件。
        """
        albums = [k.album for k in self.album_kanbans]
        dump_albums_to_toml(albums, self.theme_metadata_file)

    def __hash__(self) -> int:
        return hash((self.theme_metadata_file, self.theme_directory, self.album_kanbans))

@dataclass
class KanBan:
    """
    :param metadata_dir: 元数据目录路径
    :param resource_dir: 资源目录路径

    :var theme_kanbans: 
    """

    metadata_dir: str
    resource_dir: str

    theme_kanbans: tuple[ThemeKanBan, ...] = field(init=False)

    def __post_init__(self) -> None:
        self.metadata_dir = os.path.abspath(self.metadata_dir)
        self.resource_dir = os.path.abspath(self.resource_dir)
        self.scan()

    @logger_watched(2)
    def scan(self) -> None:
        """
        扫描文件系统。
        """
        # 元数据目录，资源目录 可以是嵌套的
        theme_mdfs = list(Path(self.metadata_dir).rglob("*.toml"))
        theme_dirs = [os.path.join(self.resource_dir, f.relative_to(self.metadata_dir).with_suffix("")) 
                      for f in theme_mdfs]

        with ThreadPoolExecutor() as executor:
            self.theme_kanbans = tuple(executor.map(ThemeKanBan, theme_mdfs, theme_dirs))

    def get_theme_kanban(self, name: str) -> ThemeKanBan | None:
        return next((k for k in self.theme_kanbans if k.theme_name == name), None)

    def __hash__(self) -> int:
        return hash((self.metadata_dir, self.resource_dir, self.theme_kanbans))
