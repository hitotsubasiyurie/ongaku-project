import itertools
from pathlib import Path
from types import SimpleNamespace

import rtoml

from ongaku.core.logger import lprint
from ongaku.core.settings import global_settings
from ongaku.core.kanban import load_albums_from_toml, album_filename, track_filenames
from ongaku.core.constants import AUDIO_EXTS
from ongaku.utils.basemodel_utils import (album_to_unique_str, track_to_unique_str, 
    albums_assignment, tracks_assignment)
from ongaku.toolkit.toolkit_utils import easy_linput
from ongaku.utils.audiofile_utils import analyze_resource_album, analyze_resource_track
from ongaku.utils.utils import dump_toml


if global_settings.language == "zh":
    PLUGIN_NAME = "归档音频资源"
elif global_settings.language == "ja":
    pass
else:
    pass


MESSAGE = SimpleNamespace()


if global_settings.language == "zh":
    MESSAGE.XX1 = "请输入一个元数据文件："
    MESSAGE.OG9 = "请输入音频资源父目录："
    MESSAGE.K98 = "请输入归档目标位置的父目录："
    MESSAGE.C99 = "匹配元数据时是否音轨数目必须相等（Y/N）（默认Y）："
    MESSAGE.D99 = "请修改归档详细文件：{}"
    MESSAGE.SRH = "请决定是否应用归档（Y/N）（默认N）："
    MESSAGE.D7I = "目标位置存在同级别资源时，是否替换成当前资源（Y/N）（默认N）："
    MESSAGE.R96 = "归档资源成功。"
elif global_settings.language == "ja":
    pass
else:
    pass


IS_APPLY = "IS_APPLY"
ALBUM_SIMILARITY = "ALBUM_SIMILARITY"
TRACK_SIMILARITY = "TRACK_SIMILARITY"

SRC_DIRECTORY = "SRC_DIRECTORY"
DST_DIRECTORY = "DST_DIRECTORY"

RESOURCE_ALBUM = "RESOURCE_ALBUM"
MATCHING_ALBUM = "MATCHING_ALBUM"

SRC_AUDIOFILE = "SRC_AUDIOFILE"
DST_AUDIOFILE = "DST_AUDIOFILE"
SRC_TRACK = "SRC_TRACK"
DST_TRACK = "DST_TRACK"


def main() -> None:

    metadata_file = easy_linput(MESSAGE.XX1, return_type=Path)
    src_parent = easy_linput(MESSAGE.OG9, return_type=Path)
    dst_parent = easy_linput(MESSAGE.K98, return_type=Path)

    filter_trackcount = easy_linput(MESSAGE.C99, default="Y", return_type=str)  != "N"

    # 扁平、存在音频 的目录 认为是专辑目录
    src_dirs = [d for d in src_parent.rglob("*") 
                if d.is_dir() 
                and all(f.is_file() for f in d.glob("*"))
                and list(itertools.chain.from_iterable(d.glob(f"*{ext}") for ext in AUDIO_EXTS))]

    # 加载 来源和目标 专辑模型
    src_albums = list(map(analyze_resource_album, src_dirs))
    dst_albums = load_albums_from_toml(metadata_file)

    archive_details = []
    archive_details_file = Path(global_settings.temp_directory, "archive_details.toml")

    # 生成 archive_details
    a_row_ind, a_col_ind, _, a_sim_matrix = albums_assignment(src_albums, dst_albums, filter_trackcount=filter_trackcount)

    for a_row, a_col in zip(a_row_ind, a_col_ind):
        src_album, dst_album = src_albums[a_row], dst_albums[a_col]

        src_dir = src_dirs[a_row]
        src_audios = list(itertools.chain.from_iterable(src_dir.glob(f"*{ext}") for ext in AUDIO_EXTS))
        src_tracks = list(map(analyze_resource_track, src_audios))

        t_row_ind, t_col_ind, t_aver_similarity, _ = tracks_assignment(src_tracks, dst_album.tracks)

        d = {}
        d[IS_APPLY] = False
        d[ALBUM_SIMILARITY] = format(a_sim_matrix[a_row][a_col], '.2f')
        d[TRACK_SIMILARITY] = format(t_aver_similarity, '.2f')
        d[SRC_DIRECTORY] = str(src_dir)
        d[DST_DIRECTORY] = str(dst_parent / album_filename(dst_album))
        d[RESOURCE_ALBUM] = album_to_unique_str(src_album)
        d[MATCHING_ALBUM] = album_to_unique_str(dst_album)
        d["track"] = []
        dst_track_names = track_filenames(dst_album)
        for t_row, t_col in zip(t_row_ind, t_col_ind):
            dd = {}
            dd[SRC_AUDIOFILE] = src_audios[t_row].name
            dd[DST_AUDIOFILE] = dst_track_names[t_col] + src_audios[t_row].suffix.lower()
            dd[SRC_TRACK] = track_to_unique_str(src_tracks[t_row])
            dd[DST_TRACK] = track_to_unique_str(dst_album.tracks[t_col])
            d["track"].append(dd)

        archive_details.append(d)

    dump_toml({str(i+1): d for i, d in enumerate(archive_details)}, archive_details_file)

    # 等待用户编辑 archive_details
    lprint(MESSAGE.D99.format(archive_details_file))
    _continue = easy_linput(MESSAGE.SRH, default="N", return_type=str)  == "Y"
    if not _continue:
        return
    
    # 应用 archive_details
    archive_details = list(rtoml.loads(archive_details_file.read_text(encoding="utf-8")).values())

    replace_same = easy_linput(MESSAGE.D7I, default="N", return_type=str)  == "Y"

    for d in archive_details:

        if not d[IS_APPLY]:
            continue

        for dd in d["track"]:

            src, dst = Path(d[SRC_DIRECTORY], dd[SRC_AUDIOFILE]), Path(d[DST_DIRECTORY], dd[DST_AUDIOFILE])
            dst.parent.mkdir(parents=True, exist_ok=True)

            # 可选替换同级
            if dst.is_file():
                if replace_same and src.is_file():
                    dst.unlink()
                    src.rename(dst)
                else:
                    src.unlink()
            
            # 有损 不替换 无损 
            elif src.suffix.lower() == ".mp3" and dst.with_suffix(".flac").exists():
                src.unlink()

            # 无损 替换 有损
            elif src.suffix.lower() == ".flac" and (dst_lossy:= dst.with_suffix(".mp3")).exists():
                src.rename(dst)
                dst_lossy.unlink()

            else:
                src.rename(dst)

    lprint(MESSAGE.R96)



