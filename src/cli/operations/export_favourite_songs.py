import itertools
import json
import re
import os
import uuid
import shutil
from collections import defaultdict
from pathlib import Path

from mutagen.flac import FLAC
from mutagen.id3 import ID3, APIC
from mutagen.mp3 import MP3

from src.core.basemodels import Album, Track
from src.core.kanban import Kanban, track_stemnames
from src.core.logger import lprint, logger
from src.core.settings import settings
from src.external import show_audio_stream_info, compress_image
from src.core.i18n import MESSAGE
from src.utils import write_audio_tags, read_audio_tags, read_audio_cover
from src.cli.common import easy_linput


OPERATION_NAME = MESSAGE.WF_20251204_194420


# 工具函数

def write_metadata(dst_file: str | Path, cover: str, album: Album, track: Track) -> None:
    """
    向 dst_file 写入元数据。
    """
    # TODO: #########################################################################归档了的专辑呢？
    # flac 格式封面限制 16 MiB
    if Path(cover).stat().st_size >= 16 * 1024 * 1024:
        lprint(MESSAGE.WF_20251204_194431.format(cover))
        compress_image(cover)

    write_audio_tags(str(dst_file), cover, 
                     album.catalognumber, album.date, album.album, 
                     str(track.tracknumber), track.title, track.artist)


# 业务函数

def get_missing_files(kanban: Kanban) -> tuple[list, list]:
    missing_favs, missing_covers = [], []

    for tk in kanban.theme_kanbans:
        for ak in tk.album_kanbans:
            idxs = [i for i, t in enumerate(ak.album.tracks) if t.mark == "1"]
            if not idxs:
                continue
            parent = ak.album_dir or ak.album_archive
            if not ak.cover_filename:
                missing_covers.append(parent)
            missing_idxs = [i for i in idxs if not ak.track_filenames[i]]
            stemnames = track_stemnames(ak.album)
            missing_favs.extend(os.path.join(parent, stemnames[i]) for i in missing_idxs)
    
    return missing_favs, missing_covers


def get_eported_map(export_dir: Path, kanban: Kanban) -> dict[tuple[int, int, int], Path]:
    exported_map = {}

    for i, theme_kanban in enumerate(kanban.theme_kanbans):
        theme_export_dir = export_dir / theme_kanban.theme_name
        if not theme_export_dir.is_dir():
            continue

        info2file = {show_audio_stream_info(str(f)): f for f in theme_export_dir.iterdir()}

        for j, album_kanban in enumerate(theme_kanban.album_kanbans):
            for k, track in enumerate(album_kanban.album.tracks):

                if track.mark != "1":
                    continue

                src_name = album_kanban.track_filenames[k]
                exported_map[(i, j, k)] = info2file.get(show_audio_stream_info(album_kanban.read_file(src_name)))

    return exported_map

# 主函数

def main() -> None:
    lprint(MESSAGE.WF_20251204_194421)

    export_dir = easy_linput(MESSAGE.WF_20251204_194422, return_type=Path)
    
    kanban = Kanban(settings.metadata_directory, settings.resource_directory, settings.archive_directory)

    # 检查缺失文件
    missing_favs, missing_covers = get_missing_files(kanban)
    if missing_favs or missing_covers:
        missing_favs and [lprint(f) for f in missing_favs] and lprint(MESSAGE.WF_20251204_194427)
        missing_covers and [lprint(f) for f in missing_covers] and lprint(MESSAGE.WF_20251204_194428)
        return
    
    # 检查封面大小
    

    # 寻找映射
    exported_map = get_eported_map(export_dir, kanban)

    # 删除脏文件，空目录
    exported = set(exported_map.values())
    dirty_files = [f for f in export_dir.rglob("*") if f.is_file() and f not in exported]
    [lprint(str(f)) for f in dirty_files]
    if not easy_linput(MESSAGE.WF_20251204_194429.format(f), default="Y", return_type=str)  == "Y":
        return
    [f.unlink() for f in dirty_files]
    [d.rmdir() for d in reversed(filter(Path.is_dir, export_dir.rglob("*"))) if not os.listdir(d)]

    # 开始导出
    total = sum(1 for tk in kanban.theme_kanbans for ak in tk.album_kanbans for t in ak.album.tracks if t.mark == "1")
    current = 0

    for i, theme_kanban in enumerate(kanban.theme_kanbans):
        theme_export_dir = export_dir / theme_kanban.theme_name
        theme_export_dir.mkdir(parents=True, exist_ok=True)

        for j, album_kanban in enumerate(theme_kanban.album_kanbans):
            album = album_kanban.album

            for k, track in enumerate(album_kanban.album.tracks):

                # 跳过非 favourite
                if track.mark != "1":
                    continue

                current += 1

                dst_file = exported_map.get((i, j, k))

                # 未导出时
                if not dst_file:
                    src_name = album_kanban.track_filenames[k]

                    # 去掉轨道号前缀 "2. 風への誓い.mp3" -> "風への誓い.mp3"
                    dst_name = Path(src_name.name.split(" ", maxsplit=1)[1])
                    shortpath = Path(theme_export_dir, dst_name)
                    longpath = Path(theme_export_dir, dst_name.with_stem(f"{dst_name.stem} {uuid.uuid3(uuid.NAMESPACE_X500, album.album)}"))
                    dst_file = shortpath if not shortpath.is_file() else longpath

                    dst_file.write_bytes(album_kanban.read_file(src_name))
                    write_metadata(dst_file, album_kanban.cover, album, track)
                    lprint(MESSAGE.WF_20251204_194423.format(current, total, dst_file))
                    continue

                # 元数据不一致或者封面不一致时
                src_tags = (album.catalognumber, album.date, album.album, str(track.tracknumber), track.title, track.artist)
                dst_tags = tuple(read_audio_tags(dst_file, standard=True).values())
                if any((v1 and v1 != v2) for v1, v2 in zip(src_tags, dst_tags)) or len(read_audio_cover) != len(album_kanban.read_file(album_kanban.cover_filename)):
                    logger.info(f"Metadata are not the same. {src_tags} {dst_tags}")
                    write_metadata(dst_file, album_kanban.cover, album, track)
                    lprint(MESSAGE.WF_20251204_194425.format(current, total, dst_file))
                    continue

                # 已导出时
                lprint(MESSAGE.WF_20251204_194424.format(current, total, src_name, dst_file))

    lprint(MESSAGE.WF_20251204_194432)


