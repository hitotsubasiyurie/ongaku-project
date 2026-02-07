import os
import pickle
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
from attrs import asdict
from cattrs import Converter
from pympler import asizeof

from src.core.basemodels import Album, Track
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


@dataclass
class ElementKanBan:
    """
    专辑元素看板。

    :param parent_path: 
    :param filename: 
    """

    parent_path: str
    """专辑目录路径 或 专辑归档文件路径。文件不存在时为专辑目录路径"""
    filename: str
    """文件名。文件不存在时为空字符串。"""

    def __post_init__(self) -> None:
        self.parent_path = os.path.abspath(self.parent_path)

    @cached_property
    def is_archive_format(self) -> bool:
        """文件是否为归档格式。文件不存在时默认为目录格式"""
        return self.filename and os.path.isfile(self.parent_path)

    @property
    def stat_result(self)-> os.stat_result | None:
        """文件属性。文件不存在时为 None"""
        if not self.filename:
            return None
        if not self.is_archive_format:
            return Path(self.parent_path, self.filename).stat()
        else:
            return FileSystemCache.rar_stats(self.parent_path).get(self.filename)

    def read_bytes(self) -> bytes:
        """
        读取文件字节数据。文件不存在时为 b""
        """
        if not self.filename:
            return b""
        if not self.is_archive_format:
            return Path(self.parent_path, self.filename).read_bytes()
        else:
            return FileSystemCache.rar_read(self.parent_path, self.filename)


@dataclass
class TrackKanBan(ElementKanBan):
    """
    音轨看板。

    :param parent_path: 
    :param filename: 
    :param track: 
    """

    track: Track
    """Track 模型"""

    def __post_init__(self) -> None:
        super().__post_init__()

    @property
    def metadata_state(self) -> MetadataState:
        """音轨元数据状态"""
        s = MetadataState.ALL_EXIST
        if not self.track.artist:
            s &= ~MetadataState.ARTIST_EXIST
        return s

    @property
    def resource_state(self) -> ResourceState:
        """音轨资源状态"""
        return _RESOURCE_STATE_MAP[Path(self.filename).suffix.lower() if self.filename else ""]

    @property
    def audio_stream_info(self) -> dict:
        """音轨音频流信息。文件不存在时为 {}"""
        if not self.filename:
            return {}
        if not self.is_archive_format:
            return show_audio_stream_info(os.path.join(self.parent_path, self.filename))
        else:
            return show_audio_stream_info(rar_read(self.parent_path, self.filename))


@dataclass
class AlbumKanBan:
    """
    专辑看板。

    :param album: 
    :param album_dir: 
    :param album_archive: 
    """

    album: Album
    """Album 模型"""
    album_dir: str
    """将会搜索的专辑目录路径。扁平地存放每一个音轨文件。优先级高"""
    album_archive: str
    """将会搜索的专辑归档路径。扁平地存放每一个音轨文件"""

    def __post_init__(self) -> None:
        self.album_dir = os.path.abspath(self.album_dir)
        self.album_archive = os.path.abspath(self.album_archive)

    @property
    def cover_kanban(self) -> ElementKanBan:
        """封面看板"""
        # 专辑目录和专辑归档 都不存在时
        if not os.path.isdir(self.album_dir) and not os.path.isfile(self.album_archive):
            return ElementKanBan(self.album_dir, "")

        # 专辑目录 优先级更高
        name2parent = {}
        if os.path.isfile(self.album_archive):
            name2parent.update({n: self.album_archive for n in _cached_rar_list(self.album_archive)})

        if os.path.isdir(self.album_dir):
            name2parent.update({n: self.album_dir for n in os.listdir(self.album_dir)})

        names = list(map(Path, name2parent.keys()))

        cover_filename = next((n.name for n in names if n.stem.lower() == COVER_STEMNAME and n.suffix.lower() in IMG_EXTS), "")
        return ElementKanBan(name2parent[cover_filename], cover_filename)

    @property
    def track_kanbans(self) -> tuple[TrackKanBan, ...]:
        """音轨看板列表"""
        # 专辑目录和专辑归档 都不存在时
        if not os.path.isdir(self.album_dir) and not os.path.isfile(self.album_archive):
            return tuple(TrackKanBan(self.album_dir, "", t) for t in self.album.tracks)

        # 专辑目录 优先级更高
        name2parent = {}
        if os.path.isfile(self.album_archive):
            name2parent.update({n: self.album_archive for n in _cached_rar_list(self.album_archive)})
        if os.path.isdir(self.album_dir):
            name2parent.update({n: self.album_dir for n in os.listdir(self.album_dir)})

        names = list(map(Path, name2parent.keys()))

        stem2ext = {n.stem: n.suffix for n in names}
        track_filenames = tuple((n+stem2ext[n]) if n in stem2ext else "" for n in track_stemnames(self.album))
        return tuple(TrackKanBan(name2parent[n] if n else self.album_dir, n, t) 
                                 for n, t in zip(track_filenames, self.album.tracks))

    @property
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
        if self.cover_kanban.filename:
            s |= MetadataState.COVER_EXIST

        return s

    @property
    def resource_state(self) -> ResourceState:
        """专辑资源状态"""
        # 元数据 无 tracks 时为 MISSING
        if not self.album.tracks:
            return ResourceState.MISSING

        states = [tk.resource_state for tk in self.track_kanbans]
        if all(states):
            return min(states)
        elif any(states):
            return ResourceState.PARTIAL
        else:
            return ResourceState.MISSING

    @property
    def is_favourite(self) -> bool:
        """是否喜欢"""
        return any(tk.is_favourite for tk in self.track_kanbans)


@dataclass
class ThemeKanBan:
    """
    主题看板。

    :param theme_metadata_file: 
    :param theme_resource_dir: 
    """

    theme_metadata_file: str
    """主题元数据文件路径"""
    theme_resource_dir: str
    """主题资源目录路径。扁平地存放每一个专辑资源目录或者专辑归档"""

    album_kanbans: tuple[AlbumKanBan, ...] = field(init=False)
    """专辑看板列表"""

    def __post_init__(self) -> None:
        self.theme_metadata_file = os.path.abspath(self.theme_metadata_file)
        self.theme_resource_dir = os.path.abspath(self.theme_resource_dir)
        self.scan()

    @cached_property
    def theme_name(self) -> str:
        """主题名"""
        return Path(self.theme_metadata_file).stem

    @cached_property
    def album_collection_progress(self) -> tuple[int, int]:
        """资源收集进度"""
        albums = [k.album for k in self.album_kanbans]
        if albums:
            return sum(k.resource_state != ResourceState.MISSING for k in self.album_kanbans), len(albums)
        return 0, 0

    @cached_property
    def track_mark_progress(self) -> tuple[int, int]:
        """标记进度"""
        albums = [k.album for k in self.album_kanbans]
        total = sum(len(a.tracks) for a in albums)
        if total:
            return sum(bool(t.mark) for a in albums for t in a.tracks), total
        return 0, 0

    @cached_property
    def start_date(self) -> tuple[str, str]:
        """最早的专辑日期"""
        dates = list(sorted(filter(None, (k.album.date for k in self.album_kanbans))))
        return dates[0] if dates else ""

    @cached_property
    def end_date(self) -> tuple[str, str]:
        """最晚的专辑日期"""
        dates = list(sorted(filter(None, (k.album.date for k in self.album_kanbans))))
        return dates[-1] if dates else ""

    def scan(self) -> None:
        """
        扫描文件系统。
        """
        albums = load_albums_from_toml(self.theme_metadata_file)
        album_dirs = [os.path.join(self.theme_resource_dir, album_stemname(a)) for a in albums]
        album_archives = [os.path.join(self.theme_resource_dir, album_stemname(a) + ARCHIVE_EXT) for a in albums]
        self.album_kanbans = tuple(AlbumKanBan(*args) for args in zip(albums, album_dirs, album_archives))

    def save_metadata_file(self) -> None:
        """
        保存元数据文件。
        """
        albums = [k.album for k in self.album_kanbans]
        dump_albums_to_toml(albums, self.theme_metadata_file)

    def __hash__(self) -> int:
        return hash((self.theme_metadata_file, self.theme_resource_dir, self.album_kanbans))


@dataclass
class KanBan:
    """
    项目看板。

    :param metadata_dir: 
    :param resource_dir: 
    """

    metadata_dir: str
    """元数据目录路径"""
    resource_dir: str
    """资源目录路径"""

    theme_kanbans: tuple[ThemeKanBan, ...] = field(init=False)
    """主题看板列表"""

    def __post_init__(self) -> None:
        self.metadata_dir = os.path.abspath(self.metadata_dir)
        self.resource_dir = os.path.abspath(self.resource_dir)
        self.scan()

    @cached_property
    def album_collection_progress(self) -> tuple[int, int]:
        """资源收集进度"""
        if self.theme_kanbans:
            colls, totals = list(zip(*[tk.album_collection_progress for tk in self.theme_kanbans]))
            return sum(colls), sum(totals)
        return 0, 0

    @cached_property
    def track_mark_progress(self) -> tuple[int, int]:
        """标记进度"""
        if self.theme_kanbans:
            marks, totals = list(zip(*[tk.track_mark_progress for tk in self.theme_kanbans]))
            return sum(marks), sum(totals)
        return 0, 0

    def scan(self) -> None:
        """
        扫描文件系统。
        """
        # 允许嵌套
        # 元数据目录、资源目录、归档目录 保持相同结构
        theme_mdfs = list(Path(self.metadata_dir).rglob("*.toml"))
        theme_res_dirs = [os.path.join(self.resource_dir, f.relative_to(self.metadata_dir).with_suffix("")) for f in theme_mdfs]

        # 默认 max_workers = cpu_count + 4
        with ThreadPoolExecutor() as executor:
            self.theme_kanbans = tuple(executor.map(ThemeKanBan, theme_mdfs, theme_res_dirs))

        # 保存 rar 缓存
        _rar_cache_file.write_bytes(pickle.dumps(_rar_cache))

    def get_theme_kanban(self, name: str) -> ThemeKanBan | None:
        if not name:
            return None
        return next((k for k in self.theme_kanbans if k.theme_name == name), None)

    def __hash__(self) -> int:
        return hash((self.metadata_dir, self.resource_dir, self.theme_kanbans))


