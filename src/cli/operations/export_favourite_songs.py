import hashlib
import itertools
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tqdm import tqdm

from src.cli.common import easy_linput
from src.cli.operations.health_check import main as health_check
from src.core.basemodels import Album, Track, TrackMark
from src.core.cache import with_cache
from src.core.i18n import MESSAGE
from src.core.kanban import Kanban, MetadataState, ResourceState
from src.core.logger import lprint, logger
from src.core.settings import settings
from src.core.storage import AUDIO_EXTS
from src.external import calculate_audio_md5, calculate_rar_audio_md5
from src.utils import write_audio_tags, read_audio_tags, read_audio_cover

OPERATION_NAME = MESSAGE.WF_20251204_194420


# 缓存方法
cached_calculate_audio_md5 = lambda audio: with_cache(calculate_audio_md5, os.path.normpath(audio), related_file=audio)
cached_calculate_rar_audio_md5 = lambda dstrar, filename: with_cache(calculate_rar_audio_md5, os.path.normpath(dstrar), filename, related_file=dstrar)

_get_audio_cover_size = lambda audio: len(read_audio_cover(audio))
_get_audio_cover_size.__name__ = "_get_audio_cover_size"
cached_get_audio_cover_size = lambda audio: with_cache(_get_audio_cover_size, os.path.normpath(audio), related_file=audio)

_read_audio_st_tags = lambda audio: tuple(read_audio_tags(audio, standard=True).values())
_read_audio_st_tags.__name__ = "_read_audio_st_tags"
cached_read_audio_st_tags = lambda audio: with_cache(_read_audio_st_tags, os.path.normpath(audio), related_file=audio)


def build_cache_audio_md5(export_dir: Path, kanban: Kanban) -> None:
    params = list(itertools.chain.from_iterable(
        ((cached_calculate_audio_md5, f), (cached_get_audio_cover_size, f), (cached_read_audio_st_tags, f)) 
        for f in export_dir.rglob("*") if f.suffix.lower() in AUDIO_EXTS)
    )

    for ak in itertools.chain.from_iterable(tk.album_kanbans for tk in kanban.theme_kanbans):
        for t, p in zip(ak.album.tracks, ak.track_paths):
            if t.mark != TrackMark.FAVOURITE:
                continue
            args = (cached_calculate_rar_audio_md5, *p) if p[0] == ak.album_archive else \
                (cached_calculate_audio_md5, os.path.join(*p))
            params.append(args)

    pbar = tqdm(total=len(params), desc=MESSAGE.WF_20260219_141601, miniters=1)
    executor = ThreadPoolExecutor()
    for args in params:
        future = executor.submit(*args)
        future.add_done_callback(lambda future: pbar.update(1))

    executor.shutdown()
    pbar.close()


def check_favourites(kanban: Kanban) -> bool:
    lprint(f"{'-'*4} {MESSAGE.WF_20260128_092704} {'-'*4}")

    missing_favs, missing_covers = [], []

    for ak in itertools.chain.from_iterable(tk.album_kanbans for tk in kanban.theme_kanbans):
        if ak.is_favourite and not MetadataState.COVER_EXIST in ak.metadata_state:
            missing_covers.append(ak.album_dir)
        missing_favs.extend(os.path.join(*p) for t, s, p in zip(ak.album.tracks, ak.track_resource_states, ak.track_paths) 
                            if t.mark == TrackMark.FAVOURITE and s == ResourceState.MISSING)

    if missing_favs or missing_covers:
        missing_favs and [lprint(f) for f in missing_favs] and lprint(MESSAGE.WF_20251204_194427)
        missing_covers and [lprint(f) for f in missing_covers] and lprint(MESSAGE.WF_20251204_194428)
        return False
    else:
        lprint(MESSAGE.WF_20260128_092707)
        return True


def write_metadata(dst_file: str | Path, cover: str, album: Album, track: Track) -> None:
    """
    向 dst_file 写入元数据。
    """
    write_audio_tags(str(dst_file), cover, album.catalognumber, album.date, album.album, str(track.tracknumber), track.title, track.artist)


# 业务函数

def get_eported_map(export_dir: Path, kanban: Kanban) -> dict[tuple[int, int, int], Path]:
    exported_map = {}

    for i, tk in enumerate(kanban.theme_kanbans):
        theme_export_dir = export_dir / os.path.relpath(tk.theme_resource_dir, kanban.resource_dir)
        if not theme_export_dir.is_dir():
            continue

        md52file = {cached_calculate_audio_md5(f): f for f in theme_export_dir.rglob("*") if f.suffix.lower() in AUDIO_EXTS}

        for j, ak in enumerate(tk.album_kanbans):
            for k, track in enumerate(ak.album.tracks):

                if track.mark != TrackMark.FAVOURITE:
                    continue

                p = ak.track_paths[k]
                md5 = cached_calculate_rar_audio_md5(*p) if p[0] == ak.album_archive else \
                    cached_calculate_audio_md5(os.path.join(*p))
                exported_map[(i, j, k)] = md52file.get(md5)

    return exported_map

# 主函数

def main() -> None:
    lprint(MESSAGE.WF_20251204_194421)

    health_check()

    export_dir = easy_linput(MESSAGE.WF_20251204_194422, return_type=Path)

    kanban = Kanban(settings.metadata_directory, settings.resource_directory)

    if not check_favourites(kanban):
        return

    build_cache_audio_md5(export_dir, kanban)

    # 寻找映射
    exported_map = get_eported_map(export_dir, kanban)

    # 删除脏文件，空目录
    exported = set(exported_map.values())
    dirty_files = [f for f in export_dir.rglob("*") if f.is_file() and f not in exported]
    if dirty_files:
        [lprint(str(f)) for f in dirty_files]
        if not easy_linput(MESSAGE.WF_20251204_194429, default="Y", return_type=str)  == "Y":
            return
        [f.unlink() for f in dirty_files]
        [d.rmdir() for d in reversed(list(filter(Path.is_dir, export_dir.rglob("*")))) if not os.listdir(d)]

    # 开始导出
    total = sum(1 for tk in kanban.theme_kanbans for ak in tk.album_kanbans for t in ak.album.tracks if t.mark == TrackMark.FAVOURITE)
    pbar = tqdm(total=total, desc=MESSAGE.WF_20251204_194420, miniters=1)

    xprint = lambda s: [logger.info(s), tqdm.write(s)]

    for i, tk in enumerate(kanban.theme_kanbans):
        theme_export_dir = export_dir / os.path.relpath(tk.theme_resource_dir, kanban.resource_dir)
        theme_export_dir.mkdir(parents=True, exist_ok=True)

        for j, ak in enumerate(tk.album_kanbans):
            album = ak.album

            for k, track in enumerate(ak.album.tracks):

                # 跳过非 favourite
                if track.mark != TrackMark.FAVOURITE:
                    continue

                pbar.update()

                src_path = ak.track_paths[k]
                # 去掉轨道号前缀 "2. 風への誓い.mp3" -> "風への誓い.mp3"
                dst_name = Path(src_path[1].split(" ", maxsplit=1)[1])
                short_dst_path = Path(theme_export_dir, dst_name)
                long_dst_path = Path(theme_export_dir, dst_name.with_stem(f"{dst_name.stem}_{hashlib.md5(album.album.encode()).hexdigest()}"))

                exported_dst = exported_map.get((i, j, k))

                # 未导出时
                if not exported_dst:
                    exported_dst = short_dst_path if not short_dst_path.is_file() else long_dst_path
                    exported_dst.write_bytes(ak.read_path_bytes(src_path))
                    write_audio_tags(exported_dst, ak.read_path_bytes(ak.cover_path), album.catalognumber, album.date, album.album, 
                                     str(track.tracknumber), track.title, track.artist)
                    xprint(MESSAGE.WF_20251204_194423.format(exported_dst))
                    continue

                if exported_dst not in (short_dst_path, long_dst_path):
                    new = short_dst_path if not short_dst_path.is_file() else long_dst_path
                    exported_dst.rename(new)
                    exported_dst = new

                # 元数据不一致或者封面不一致时
                src_tags = (album.catalognumber, album.date, album.album, str(track.tracknumber), track.title, track.artist)
                dst_tags = cached_read_audio_st_tags(exported_dst)
                if any((v1 and v1 != v2) for v1, v2 in zip(src_tags, dst_tags)) or cached_get_audio_cover_size(exported_dst) != ak.cover_stat_result.st_size:
                    logger.info(f"Metadata are not the same. {src_tags} {dst_tags}")
                    write_audio_tags(exported_dst, ak.read_path_bytes(ak.cover_path), album.catalognumber, album.date, album.album, 
                                     str(track.tracknumber), track.title, track.artist)
                    xprint(MESSAGE.WF_20251204_194425.format(exported_dst))
                    continue

    pbar.close()
    lprint(MESSAGE.WF_20251204_194432)


