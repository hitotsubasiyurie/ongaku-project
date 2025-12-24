import os
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import IntEnum, IntFlag
from functools import cached_property
from pathlib import Path
from threading import Lock

import rtoml

from src.core.basemodels import Album
from src.core.constants import IMG_EXTS, ARCHIVE_EXT
from src.core.settings import global_settings
from src.utils import legalize_filename, dump_toml
from src.external import rar_list, rar_read, rar_stats


################################################################################
### 缓存 rar_list 方法
################################################################################


_rar_list_cache_lock = Lock()
_rar_list_cache_file = Path(global_settings.temp_directory, "rar_list_cache.json")
try:
    _rar_list_cache = json.loads(_rar_list_cache_file.read_text(encoding="utf-8"))
except Exception:
    _rar_list_cache = {}


def _cached_rar_list(dstrar: str) -> list[str]:
    """
    带缓存的列出压缩包内的文件。
    """
    mtime = str(os.stat(dstrar).st_mtime)

    if val:= _rar_list_cache.get(dstrar, {}).get(mtime, []):
        return val
    
    filenames = rar_list(dstrar)

    with _rar_list_cache_lock: _rar_list_cache[dstrar] = {mtime: filenames}

    return filenames


def _save_rar_list_cache() -> None:
    """
    保存缓存文件。
    """
    with _rar_list_cache_lock: 
        _rar_list_cache_file.write_text(json.dumps(_rar_list_cache, ensure_ascii=False, indent=4), encoding="utf-8")


################################################################################
### 看板
################################################################################


ALBUM_STEMNAME = "[{catalognumber}] [{date}] {album} [{trackcounts}]"
TRACK_STEMNAME = "{tracknumber}. {title}"
COVER_STEMNAME = "cover"


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
    """
    ds = list(map(Album.model_dump, albums))
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
    albums = [Album(**d) for d in ds]
    return albums


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
    NONE         = 0b000000
    TITLE_EXIST  = 0b000001
    DATE_EXIST   = 0b000010
    CATNO_EXIST  = 0b000100
    TRACK_EXIST  = 0b001000
    ARTIST_EXIST = 0b010000
    COVER_EXIST  = 0b100000


@dataclass
class AlbumKanBan:
    """
    专辑看板。

    :param album: 
    :param album_dir: 
    :param album_archive: 
    """

    album: Album
    """专辑模型"""
    album_dir: str
    """将会搜索的专辑目录路径。扁平地存放每一个音轨文件"""
    album_archive: str
    """将会搜索的专辑归档路径。扁平地存放每一个音轨文件"""

    cover_filename: str = field(init=False)
    """封面文件名。封面不存在时为空字符串。"""
    track_filenames: tuple[str, ...] = field(init=False)
    """音轨文件名列表。文件不存在时为空字符串。"""

    def __post_init__(self) -> None:
        self.album_dir = os.path.abspath(self.album_dir)
        self.album_archive = os.path.abspath(self.album_archive)
        self.scan()

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
        if self.cover_filename:
            s |= MetadataState.COVER_EXIST

        return s

    @cached_property
    def track_res_states(self) -> tuple[ResourceState, ...]:
        """专辑轨道资源状态列表"""
        _map = {"": ResourceState.MISSING, ".mp3": ResourceState.LOSSY, ".flac": ResourceState.LOSSLESS}
        states = tuple(_map[Path(f).suffix.lower() if f else ""] for f in self.track_filenames)
        return states

    @cached_property
    def album_res_state(self) -> ResourceState:
        """专辑资源状态"""
        # 元数据 无 tracks 时为 MISSING
        if not self.album.tracks:
            s = ResourceState.MISSING
        elif all(self.track_res_states):
            s = min(self.track_res_states)
        elif any(self.track_res_states):
            s = ResourceState.PARTIAL
        else:
            s = ResourceState.MISSING

        return s

    @cached_property
    def is_favourite(self) -> bool:
        """是否喜欢"""
        return any(t.mark == "1" for t in self.album.tracks)

    @cached_property
    def track_stat_results(self) -> tuple[os.stat_result | None, ...]:
        """音轨文件属性列表"""
        if not os.path.isdir(self.album_dir) and not os.path.isfile(self.album_archive):
            return (None, ) * len(self.album.tracks)
        if os.path.isdir(self.album_dir):
            return tuple(Path(self.album_dir, n).stat() if n else None for n in self.track_filenames)
        elif os.path.isfile(self.album_archive):
            return rar_stats(self.album_archive, self.track_filenames)

    def scan(self) -> None:
        """
        扫描文件系统。
        """
        # 专辑目录和专辑归档 都不存在时
        if not os.path.isdir(self.album_dir) and not os.path.isfile(self.album_archive):
            self.cover_filename, self.track_filenames = "", ("",) * len(self.album.tracks)
            return
        
        # 优先搜索 专辑目录
        if os.path.isdir(self.album_dir):
            names = os.listdir(self.album_dir)
        elif os.path.isfile(self.album_archive):
            names = _cached_rar_list(self.album_archive)
        
        names = list(map(Path, names))

        self.cover_filename = next((n.name for n in names if n.stem.lower() == COVER_STEMNAME and n.suffix.lower() in IMG_EXTS), "")
        
        stem2ext = {n.stem: n.suffix for n in names}
        self.track_filenames = tuple((n+stem2ext[n]) if n in stem2ext else "" for n in track_stemnames(self.album))
        
        # 失效缓存
        self.invalidate_cache()

    def read_file(self, filename: str) -> bytes | None:
        """
        读取文件。
        """
        if os.path.isdir(self.album_dir):
            return Path(self.album_dir, filename).read_bytes()
        elif os.path.isfile(self.album_archive):
            return rar_read(self.album_archive, filename)

    def invalidate_cache(self) -> None:
        """
        失效缓存。
        """
        names = ["metadata_state", "track_res_states", "album_res_state", "is_favourite", "track_stat_results"]
        [self.__dict__.pop(n, None) for n in names]

    def __hash__(self) -> int:
        return hash((self.album, self.album_dir, self.album_archive, self.cover_filename, self.track_filenames))


@dataclass
class ThemeKanBan:
    """
    主题看板。

    :param theme_metadata_file: 
    :param theme_resource_dir: 
    :param theme_archive_dir: 
    """

    theme_metadata_file: str
    """主题元数据文件路径"""
    theme_resource_dir: str
    """主题资源目录路径。扁平地存放每一个专辑资源目录"""
    theme_archive_dir: str
    """主题归档目录路径。扁平地存放每一个专辑归档文件"""

    album_kanbans: tuple[AlbumKanBan, ...] = field(init=False)
    """专辑看板列表"""

    def __post_init__(self) -> None:
        self.theme_metadata_file = os.path.abspath(self.theme_metadata_file)
        self.theme_resource_dir = os.path.abspath(self.theme_resource_dir)
        self.theme_archive_dir = os.path.abspath(self.theme_archive_dir)
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
            return sum(k.album_res_state != ResourceState.MISSING for k in self.album_kanbans), len(albums)
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
        album_archives = [os.path.join(self.theme_archive_dir, album_stemname(a) + ARCHIVE_EXT) for a in albums]
        self.album_kanbans = tuple(AlbumKanBan(*args) for args in zip(albums, album_dirs, album_archives))

        # 失效缓存
        self.invalidate_cache()

    def invalidate_cache(self) -> None:
        """
        失效缓存。
        """
        # 先失效子看板缓存 再失效自身缓存
        [ak.invalidate_cache() for ak in self.album_kanbans]
        names = ["theme_name", "album_collection_progress", "track_mark_progress", "start_date", "end_date"]
        [self.__dict__.pop(n, None) for n in names]

    def save_metadata_file(self) -> None:
        """
        保存元数据文件。
        """
        albums = [k.album for k in self.album_kanbans]
        dump_albums_to_toml(albums, self.theme_metadata_file)

    def __hash__(self) -> int:
        return hash((self.theme_metadata_file, self.theme_resource_dir, self.theme_archive_dir, self.album_kanbans))


@dataclass
class KanBan:
    """
    项目看板。

    :param metadata_dir: 
    :param resource_dir: 
    :param archive_dir: 
    """

    metadata_dir: str
    """元数据目录路径"""
    resource_dir: str
    """资源目录路径"""
    archive_dir: str
    """归档目录路径"""

    theme_kanbans: tuple[ThemeKanBan, ...] = field(init=False)
    """主题看板列表"""

    def __post_init__(self) -> None:
        self.metadata_dir = os.path.abspath(self.metadata_dir)
        self.resource_dir = os.path.abspath(self.resource_dir)
        self.archive_dir = os.path.abspath(self.archive_dir)
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
        theme_arch_dirs = [os.path.join(self.archive_dir, f.relative_to(self.metadata_dir).with_suffix("")) for f in theme_mdfs]

        with ThreadPoolExecutor() as executor:
            self.theme_kanbans = tuple(executor.map(ThemeKanBan, theme_mdfs, theme_res_dirs, theme_arch_dirs))

        # 保存 rar_list 缓存
        _save_rar_list_cache()

    def get_theme_kanban(self, name: str) -> ThemeKanBan | None:
        if not name:
            return None
        return next((k for k in self.theme_kanbans if k.theme_name == name), None)

    def invalidate_cache(self) -> None:
        """
        失效缓存。
        """
        # 先失效子看板缓存 再失效自身缓存
        [tk.invalidate_cache() for tk in self.theme_kanbans]
        names = ["album_collection_progress", "track_mark_progress"]
        [self.__dict__.pop(n, None) for n in names]
    
    def __hash__(self) -> int:
        return hash((self.metadata_dir, self.resource_dir, self.archive_dir, self.theme_kanbans))


