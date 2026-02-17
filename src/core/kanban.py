import hashlib
import os
import pickle
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from enum import IntEnum, IntFlag
from functools import cached_property
from pathlib import Path
from threading import Lock
from typing import Callable, Any

from attrs import define, field
from pympler import asizeof

from src.core.basemodels import Album, TrackMark
from src.core.constants import IMG_EXT, ARCHIVE_EXT
from src.core.settings import settings
from src.external import rar_list, rar_read, rar_stats, show_audio_stream_info
from src.core.storage import album_stemname, track_stemnames, dump_albums_to_toml, load_albums_from_toml, \
    COVER_NAME


################################################################################
### 缓存
################################################################################


class FunctionCallCache:
    """函数调用缓存"""

    _CACHE_LOCK = Lock()
    _CACHE_FILE = Path(settings.temp_directory, "function_call_cache")
    _CACHE: OrderedDict = None
    # 缓存 大小 MiB
    _MAX_SIZE = 50 * 1024 * 1024

    @staticmethod
    def load() -> None:
        """
        加载函数调用缓存。
        """
        try:
            FunctionCallCache._CACHE = pickle.loads(FunctionCallCache._CACHE_FILE.read_bytes())
        except Exception:
            FunctionCallCache._CACHE = OrderedDict()

    @staticmethod
    def save() -> None:
        """
        保存函数调用缓存。
        """
        with FunctionCallCache._CACHE_LOCK:
            items = list(FunctionCallCache._CACHE.items())

        total_size = 0
        keep_from = len(items)

        for i in range(len(items) - 1, -1, -1):
            total_size += asizeof.asizeof(items[i][1])
            if total_size > FunctionCallCache._MAX_SIZE:
                break
            keep_from = i

        with FunctionCallCache._CACHE_LOCK:
            FunctionCallCache._CACHE = OrderedDict(items[keep_from:])
            FunctionCallCache._CACHE_FILE.write_bytes(pickle.dumps(FunctionCallCache._CACHE))

    @staticmethod
    def rar_list(dstrar: str) -> list[str]:
        return FunctionCallCache._with_cache_call(rar_list, dstrar, related_file=dstrar)

    @staticmethod
    def rar_stats(dstrar: str) -> dict[str, os.stat_result]:
        return FunctionCallCache._with_cache_call(rar_stats, dstrar, related_file=dstrar)

    @staticmethod
    def show_audio_stream_info(filepath: str) -> dict:
        return FunctionCallCache._with_cache_call(show_audio_stream_info, filepath, related_file=filepath)

    @staticmethod
    def show_rar_audio_stream_info(dstrar: str, filename: str) -> dict:
        func = lambda x, y: show_audio_stream_info(rar_read(x, y))
        func.__name__ = "show_rar_audio_stream_info"
        return FunctionCallCache._with_cache_call(func, dstrar, filename, related_file=dstrar)

    @staticmethod
    def _with_cache_call(func: Callable, *args, related_file: str = "") -> Any:
        """
        :param related_file: 关联的文件
        """
        if related_file:
            stat = os.stat(related_file)
            key = FunctionCallCache._make_key((func.__name__, related_file, stat.st_mtime, stat.st_size) + args, {}, False)
        else:
            key = FunctionCallCache._make_key((func.__name__, ) + args, {}, False)

        with FunctionCallCache._CACHE_LOCK:
            val = FunctionCallCache._CACHE.get(key)
            if val is not None:
                FunctionCallCache._CACHE.move_to_end(key)
                return val

        val = func(*args)

        with FunctionCallCache._CACHE_LOCK:
            FunctionCallCache._CACHE[key] = val
            FunctionCallCache._CACHE.move_to_end(key)

        return val

    def _make_key(*args) -> str:
        key = ":".join(str(a) for a in args)
        return hashlib.md5(key.encode()).hexdigest()


# 加载 缓存
FunctionCallCache.load()


################################################################################
### 看板
################################################################################


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


@define(slots=False)
class AlbumKanban:
    """
    专辑看板。
    对专辑元数据和音轨文件的统计属性的汇总。
    """

    album: Album
    """专辑模型"""
    album_dir: str = field(converter=os.path.abspath)
    """将会搜索的专辑目录路径。扁平地存放每一个音轨文件。优先级高"""
    album_archive: str = field(converter=os.path.abspath)
    """将会搜索的专辑归档路径。扁平地存放每一个音轨文件"""

    @cached_property
    def cover_path(self) -> tuple[str, str]:
        """
        专辑封面路径.
        封面文件不存在时，path 为 (album_dir, COVER_NAME)
        """
        if Path(self.album_dir, COVER_NAME).is_file():
            return self.album_dir, COVER_NAME
        if os.path.isfile(self.album_archive) and COVER_NAME in FunctionCallCache.rar_list(self.album_archive):
            return self.album_archive, COVER_NAME
        return self.album_dir, COVER_NAME

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
            stem2path.update({Path(n).stem: (self.album_archive, n) for n in FunctionCallCache.rar_list(self.album_archive)})
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
        if self.cover_path[0] == self.album_archive or Path(*self.cover_path).is_file():
            s |= MetadataState.COVER_EXIST

        return s

    @cached_property
    def track_resource_states(self) -> tuple[ResourceState, ...]:
        """音轨资源状态列表"""
        return tuple(_RESOURCE_STATE_MAP.get(Path(p[1]).suffix.lower(), ResourceState.MISSING) for p in self.track_paths)

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
        arch_stats = FunctionCallCache.rar_stats(self.album_archive) if os.path.isfile(self.album_archive) else {}
        dir_stats = {p.name: p.stat() for p in Path(self.album_dir).iterdir()} if os.path.isdir(self.album_dir) else {}
        return tuple(arch_stats.get(p[1]) if p[0] == self.album_archive else dir_stats.get(p[1]) for p in self.track_paths)

    @cached_property
    def cover_stat_result(self) -> os.stat_result | None:
        """封面文件属性"""
        if self.cover_path[0] == self.album_archive:
            return FunctionCallCache.rar_stats(self.album_archive)[self.cover_path[1]]
        p = Path(*self.cover_path)
        return p.stat() if p.is_file() else None

    def read_path_bytes(self, p: tuple[str, str]) -> bytes:
        """
        读取路径文件字节数据。路径文件不存在时返回空字节。

        :param p: 封面文件路径或音轨文件路径
        """
        if p[0] == self.album_archive:
            return rar_read(*p)
        path = Path(*p)
        return path.read_bytes() if path.is_file() else b""

    def refresh(self) -> None:
        """
        刷新缓存。
        """
        # 先刷新子看板缓存 再刷新自身缓存
        attrs = ("cover_path", "track_paths", "metadata_state", "track_resource_states", 
                 "resource_state", "is_favourite", "track_stat_results", "cover_stat_result")
        [self.__dict__.pop(a, None) for a in attrs]


@define(slots=False)
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


@define(slots=False)
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
        
        # 保存函数调用缓存
        FunctionCallCache.save()

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



