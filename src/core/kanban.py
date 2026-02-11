import os
import pickle
import itertools
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import IntEnum, IntFlag
from functools import cached_property
from pathlib import Path
from threading import Lock
from collections import OrderedDict
from typing import Callable, Any
from functools import _make_key

import rtoml
from cattrs import Converter
from pympler import asizeof
from attrs import define, field, validators, asdict

from src.core.basemodels import Album, Track, TrackMark
from src.core.constants import IMG_EXT, ARCHIVE_EXT
from src.core.settings import settings
from src.utils import legalize_filename, dump_toml
from src.external import rar_list, rar_read, rar_stats, rar_add, show_audio_stream_info


################################################################################
### 缓存
################################################################################


class FileSystemCache:
    """文件系统缓存"""

    _CACHE_LOCK = Lock()
    _CACHE_FILE = Path(settings.temp_directory, "filesystem_cache")
    _CACHE: OrderedDict = None
    # 缓存 大小 MiB
    _MAX_SIZE = 50 * 1024 * 1024

    @staticmethod
    def save() -> None:
        with FileSystemCache._CACHE_LOCK:
            items = list(FileSystemCache._CACHE.items())

        total_size = 0
        keep_from = len(items)

        for i in range(len(items) - 1, -1, -1):
            total_size += asizeof.asizeof(items[i][1])
            if total_size > FileSystemCache._MAX_SIZE:
                break
            keep_from = i

        with FileSystemCache._CACHE_LOCK:
            FileSystemCache._CACHE = OrderedDict(items[keep_from:])
            FileSystemCache._CACHE_FILE.write_bytes(pickle.dumps(FileSystemCache._CACHE))

    @staticmethod
    def rar_list(dstrar: str) -> list[str]:
        return FileSystemCache._with_cache_call(rar_list, dstrar, related_file=dstrar)

    @staticmethod
    def rar_stats(dstrar: str) -> dict[str, os.stat_result]:
        return FileSystemCache._with_cache_call(rar_stats, dstrar, related_file=dstrar)

    @staticmethod
    def show_audio_stream_info(filepath: str) -> dict:
        return FileSystemCache._with_cache_call(show_audio_stream_info, filepath, related_file=filepath)

    @staticmethod
    def show_rar_audio_stream_info(dstrar: str, filename: str) -> dict:
        func = lambda x, y: show_audio_stream_info(rar_read(x, y))
        func.__name__ = "show_rar_audio_stream_info"
        return FileSystemCache._with_cache_call(func, dstrar, filename, related_file=dstrar)

    @staticmethod
    def _with_cache_call(func: Callable, *args, related_file: str = "") -> Any:
        """
        :param related_file: 关联的文件
        """
        if related_file:
            stat = os.stat(related_file)
            key = _make_key((func.__name__, related_file, stat.st_mtime, stat.st_size) + args)
        else:
            key = _make_key((func.__name__, ) + args)

        with FileSystemCache._CACHE_LOCK:
            val = FileSystemCache._CACHE.get(key)
            if val is not None:
                FileSystemCache._CACHE.move_to_end(key)
                return val

        val = func(*args)

        with FileSystemCache._CACHE_LOCK:
            FileSystemCache._CACHE[key] = val
            FileSystemCache._CACHE.move_to_end(key)

        return val


# 加载 缓存
try:
    FileSystemCache._CACHE = pickle.loads(FileSystemCache._CACHE_FILE.read_bytes())
except Exception:
    FileSystemCache._CACHE = OrderedDict()


################################################################################
### 常量、枚举
################################################################################


# 专辑文件名主干
ALBUM_STEMNAME = "[{catalognumber}] [{date}] {album} [{trackcounts}]"
# 音轨文件名主干
TRACK_STEMNAME = "{tracknumber}. {title}"


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
        d["tracks"] = [{"tracknumber": t[0], "title": t[1], "artist": t[2], "mark": t[3]} 
                       for t in d["tracks"]]
    converter = Converter()
    albums = [converter.structure(d, Album) for d in ds]
    return albums


class ResourceState(IntEnum):
    """专辑资源状态"""
    # 完整无损
    LOSSLESS = 3
    # 完整有损
    LOSSY = 2
    # 不完整
    PARTIAL = 1
    # 缺失
    MISSING = 0


_RESOURCE_STATE_MAP = {
    "": ResourceState.MISSING, 
    ".mp3": ResourceState.LOSSY, 
    ".flac": ResourceState.LOSSLESS
}


class MetadataState(IntFlag):
    """专辑元数据文件状态"""
    NONE         = 0b000000
    TITLE_EXIST  = 0b000001
    DATE_EXIST   = 0b000010
    CATNO_EXIST  = 0b000100
    TRACK_EXIST  = 0b001000
    ARTIST_EXIST = 0b010000
    COVER_EXIST  = 0b100000
    ALL_EXIST    = 0b111111


################################################################################
### 看板
################################################################################


@define()
class AlbumKanban:
    """
    专辑看板。
    对专辑元数据和音轨文件的统计属性的汇总。
    """

    album: Album = field(validator=validators.instance_of(Album))
    """专辑模型"""
    album_dir: str = field(converter=os.path.abspath)
    """将会搜索的专辑目录路径。扁平地存放每一个音轨文件。优先级高"""
    album_archive: str = field(converter=os.path.abspath)
    """将会搜索的专辑归档路径。扁平地存放每一个音轨文件"""

    @cached_property
    def cover_path(self) -> str:
        """专辑封面路径"""
        return os.path.join(settings.cover_directory, f"{album_stemname(self.album)}{IMG_EXT}")

    @cached_property
    def track_paths(self) -> tuple[tuple[str, str], ...]:
        """
        音轨文件路径列表。
        每个 path 为元组 (parent, filename)。
        音轨文件不存在时，path 为 (album_dir, stemname)
        """
        stemnames = track_stemnames(self.album)

        stem2path = {n: (self.album_dir, n) for n in stemnames}

        if os.path.isfile(self.album_archive):
            stem2path.update({Path(n).stem: (self.album_archive, n) for n in FileSystemCache.rar_list(self.album_archive)})
        if os.path.isdir(self.album_dir):
            stem2path.update({Path(n).stem: (self.album_dir, n) for n in os.listdir(self.album_dir)})

        return tuple(stem2path[n] for n in stemnames)

    @cached_property
    def metadata_state(self) -> MetadataState:
        """专辑元数据状态"""
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
        if os.path.isfile(self.cover_path):
            s |= MetadataState.COVER_EXIST

        return s

    @cached_property
    def track_resource_states(self) -> tuple[ResourceState, ...]:
        """音轨资源状态列表"""
        return tuple(_RESOURCE_STATE_MAP[Path(p[1]).suffix.lower()] for p in self.track_paths)

    @cached_property
    def resource_state(self) -> ResourceState:
        """专辑资源状态"""
        # 元数据没有 tracks 信息时为 MISSING
        if not self.album.tracks:
            s = ResourceState.MISSING
        elif all(self.track_resource_states):
            s = min(self.track_resource_states)
        elif any(self.track_resource_states):
            s = ResourceState.PARTIAL
        else:
            s = ResourceState.MISSING

        return s

    @cached_property
    def is_favourite(self) -> bool:
        """是否喜欢"""
        return any(t.mark == TrackMark.FAVOURITE for t in self.album.tracks)

    @cached_property
    def track_stat_results(self) -> tuple[os.stat_result | None, ...]:
        """音轨文件属性列表"""
        arch_stats = FileSystemCache.rar_stats(self.album_archive) if os.path.isfile(self.album_archive) else {}
        dir_stats = {p.name: p.stat() for p in Path(self.album_dir).iterdir()} if os.path.isdir(self.album_dir) else {}
        return tuple(arch_stats.get(p[1]) if p[0] == self.album_archive else dir_stats.get(p[1]) for p in self.track_paths)

    def read_track_bytes(self, p: tuple[str, str]) -> bytes | None:
        """
        读取音轨文件字节数据。
        
        :param p: 音轨文件路径
        """
        return rar_read(*p) if p[0] == self.album_archive else Path(*p).read_bytes()

    def refresh(self) -> None:
        """
        刷新缓存。
        """
        # 先刷新子看板缓存 再刷新自身缓存
        attrs = ("cover_path", "track_paths", "metadata_state", "track_resource_states", 
                 "resource_state", "is_favourite", "track_stat_results")
        [self.__dict__.pop(a, None) for a in attrs]


@define()
class ThemeKanban:
    """主题看板"""

    theme_metadata_file: str = field(converter=os.path.abspath)
    """主题元数据文件路径"""
    theme_resource_dir: str = field(converter=os.path.abspath)
    """主题资源目录路径。扁平地存放每一个专辑目录或专辑归档"""

    album_kanbans: tuple[AlbumKanban, ...] = field(init=False)
    """专辑看板列表"""

    def __attrs_post_init__(self) -> None:
        # 创建 主题目录
        os.makedirs(self.theme_resource_dir, exist_ok=True)

        albums = load_albums_from_toml(self.theme_metadata_file)
        album_dirs = [os.path.join(self.theme_resource_dir, album_stemname(a)) for a in albums]
        album_archives = [os.path.join(self.theme_resource_dir, f"{album_stemname(a)}{ARCHIVE_EXT}") for a in albums]
        self.album_kanbans = tuple(AlbumKanban(*args) for args in zip(albums, album_dirs, album_archives))

    @cached_property
    def theme_name(self) -> str:
        """主题名"""
        return Path(self.theme_metadata_file).stem

    @cached_property
    def collecting_progress(self) -> tuple[int, int]:
        """资源收集进度"""
        states = [s != ResourceState.MISSING for ak in self.album_kanbans for s in ak.track_resource_states]
        if states: return sum(states), len(states)
        return 0, 0

    @cached_property
    def marking_progress(self) -> tuple[int, int]:
        """标记进度"""
        marks = [t.mark != TrackMark.UNKNOWN for ak in self.album_kanbans for t in ak.album.tracks]
        if marks: return sum(marks), len(marks)
        return 0, 0

    @cached_property
    def start_date(self) -> str:
        """最早的专辑日期"""
        dates = list(sorted(filter(None, (ak.album.date for ak in self.album_kanbans))))
        return dates[0] if dates else ""

    @cached_property
    def end_date(self) -> str:
        """最晚的专辑日期"""
        dates = list(sorted(filter(None, (ak.album.date for ak in self.album_kanbans))))
        return dates[-1] if dates else ""

    def save_metadata_file(self) -> None:
        """
        保存元数据文件。
        """
        albums = [ak.album for ak in self.album_kanbans]
        dump_albums_to_toml(albums, self.theme_metadata_file)

    def refresh(self) -> None:
        """
        刷新缓存。
        """
        # 先刷新子看板缓存 再刷新自身缓存
        [ak.refresh() for ak in self.album_kanbans]
        attrs = ("collecting_progress", "marking_progress", "start_date", "end_date")
        [self.__dict__.pop(a, None) for a in attrs]


@define()
class Kanban:
    """总看板"""

    metadata_dir: str = field(converter=os.path.abspath)
    """元数据目录路径"""
    resource_dir: str = field(converter=os.path.abspath)
    """资源目录路径"""

    theme_kanbans: tuple[ThemeKanban, ...] = field(init=False)
    """主题看板列表"""

    def __attrs_post_init__(self) -> None:
        # 创建 目录
        os.makedirs(self.metadata_dir, exist_ok=True)
        os.makedirs(self.resource_dir, exist_ok=True)

        # 允许嵌套
        # 元数据目录、资源目录、归档目录 保持相同结构
        mdfs = list(Path(self.metadata_dir).rglob("*.toml"))
        paths = [os.path.join(self.resource_dir, f.relative_to(self.metadata_dir).with_suffix("")) for f in mdfs]

        # 默认 max_workers = cpu_count + 4
        with ThreadPoolExecutor() as executor:
            self.theme_kanbans = tuple(executor.map(ThemeKanban, mdfs, paths))

    @cached_property
    def collecting_progress(self) -> tuple[int, int]:
        """资源收集进度"""
        if not self.theme_kanbans:
            return 0, 0
        colls, totals = list(zip(*(tk.collecting_progress for tk in self.theme_kanbans)))
        return sum(colls), sum(totals)
        
    @cached_property
    def marking_progress(self) -> tuple[int, int]:
        """标记进度"""
        if not self.theme_kanbans:
            return 0, 0
        marks, totals = list(zip(*[tk.marking_progress for tk in self.theme_kanbans]))
        return sum(marks), sum(totals)

    def get_theme_kanban(self, name: str) -> ThemeKanban | None:
        if not name:
            return None
        return next((k for k in self.theme_kanbans if k.theme_name == name), None)

    def refresh(self) -> None:
        """
        刷新缓存。
        """
        # 先刷新子看板缓存 再刷新自身缓存
        [tk.refresh() for tk in self.theme_kanbans]
        attrs = ("collecting_progress", "marking_progress")
        [self.__dict__.pop(a, None) for a in attrs]




