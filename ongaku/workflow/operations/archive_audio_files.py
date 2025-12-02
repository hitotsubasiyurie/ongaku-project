import shutil
import itertools
from pathlib import Path

import rtoml

from ongaku.core.logger import lprint
from ongaku.core.settings import global_settings
from ongaku.core.kanban import load_albums_from_toml, album_filename, track_filenames
from ongaku.core.basemodels import Album
from ongaku.core.constants import AUDIO_EXTS
from ongaku.workflow.common import (easy_linput, analyze_album, analyze_track, album_to_unique_str, 
    track_to_unique_str, albums_assignment, tracks_assignment, count_album_similarity)
from ongaku.utils import dump_toml


if global_settings.language == "zh":
    OPERATION_NAME = "归档音频资源"
    class MESSAGE:
        OLI4J5 = """
主题目录的父目录：
    例如 "D:\\ongaku-resource\\AnimeComicGame" ，将会在这里创建主题目录 "D:\\ongaku-resource\\AnimeComicGame\\Aチャンネル [A频道] [A-Channel]"
是否替换同级别资源：
    自动以 flac 替换 mp3 。
    替换同级别资源时，会以 flac 替换 flac ，以 mp3 替换 mp3 。
    """
        XX1GO9 = "请输入元数据文件："
        OG955I = "请输入音频资源父目录："
        K98JF4 = "请输入主题目录的父目录："
        C99DV4 = "匹配元数据时是否音轨数目必须相等（Y/N）（默认Y）："
        D998O9 = "请修改归档详细文件：{}"
        SRHBNM = "请决定是否应用归档（Y/N）（默认N）："
        D7IAA4 = "是否替换同级别资源（Y/N）（默认N）："
        R96CC5 = "归档音频资源已完成。"
elif global_settings.language == "ja":
    pass
else:
    pass


################ 业务函数 ################

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


def generate_archive_detail(theme_directory: Path, dst_album: Album, src_dir: Path, 
                             src_album: Album = None, album_similarity: float = None) -> dict:
    """生成归档细节"""
    # 计算 可选参数
    if not src_album:
        src_album = analyze_album(src_dir)
    if not album_similarity:
        album_similarity = count_album_similarity(src_album, dst_album)

    src_audios = list(itertools.chain.from_iterable(src_dir.glob(f"*{ext}") for ext in AUDIO_EXTS))
    src_tracks = list(map(analyze_track, src_audios))

    t_row_ind, t_col_ind, t_aver_similarity, _ = tracks_assignment(src_tracks, dst_album.tracks)

    d = {}
    d[IS_APPLY] = False
    d[ALBUM_SIMILARITY] = format(album_similarity, '.2f')
    d[TRACK_SIMILARITY] = format(t_aver_similarity, '.2f')
    d[SRC_DIRECTORY] = str(src_dir)
    d[DST_DIRECTORY] = str(Path(theme_directory, album_filename(dst_album)))
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

    return d


def apply_archive_detail(detail: dict, is_replace_same: bool) -> None:
    """应用归档细节"""
    if not detail[IS_APPLY]:
        return

    for dd in detail["track"]:

        src, dst = Path(detail[SRC_DIRECTORY], dd[SRC_AUDIOFILE]).resolve(), Path(detail[DST_DIRECTORY], dd[DST_AUDIOFILE]).resolve()
        dst.parent.mkdir(parents=True, exist_ok=True)

        # 跳过 源等于目标 
        if src == dst:
            continue

        # 跳过 源不存在
        if not src.is_file():
            continue

        # 源，目标 同级（同名）
        if dst.is_file():
            if is_replace_same:
                dst.unlink()
                shutil.move(src, dst)
            else:
                src.unlink()

        # 源有损，目标无损
        elif src.suffix.lower() == ".mp3" and dst.with_suffix(".flac").is_file():
            src.unlink()

        # 源无损，目标有损
        elif src.suffix.lower() == ".flac" and (dst_lossy:= dst.with_suffix(".mp3")).is_file():
            shutil.move(src, dst)
            dst_lossy.unlink()
        # 无目标资源
        else:
            shutil.move(src, dst)


################ 主函数 ################

def main() -> None:
    lprint(MESSAGE.OLI4J5)

    metadata_file = easy_linput(MESSAGE.XX1GO9, return_type=Path)
    src_parent = easy_linput(MESSAGE.OG955I, return_type=Path)
    dst_parent = easy_linput(MESSAGE.K98JF4, return_type=Path)
    filter_trackcount = easy_linput(MESSAGE.C99DV4, default="Y", return_type=str)  == "Y"

    archive_details_file = Path(global_settings.temp_directory, "archive_details.toml")

    # 存在音频 的目录 认为是专辑目录
    src_dirs = [d for d in src_parent.rglob("*") 
                if d.is_dir() 
                and list(itertools.chain.from_iterable(d.glob(f"*{ext}") for ext in AUDIO_EXTS))]

    # 加载 来源和目标 专辑模型
    src_albums = list(map(analyze_album, src_dirs))
    dst_albums = load_albums_from_toml(metadata_file)

    # 生成 archive_details
    archive_details = []
    a_row_ind, a_col_ind, _, a_sim_matrix = albums_assignment(src_albums, dst_albums, filter_trackcount=filter_trackcount)

    for a_row, a_col in zip(a_row_ind, a_col_ind):
        detail = generate_archive_detail(Path(dst_parent, metadata_file.stem), dst_albums[a_col], 
                                         src_dirs[a_row], src_albums[a_row], a_sim_matrix[a_row][a_col])
        archive_details.append(detail)

    dump_toml({str(i+1): d for i, d in enumerate(archive_details)}, archive_details_file)

    # 等待用户编辑 archive_details
    lprint(MESSAGE.D998O9.format(archive_details_file))
    if not easy_linput(MESSAGE.SRHBNM, default="N", return_type=str)  == "Y":
        return
    
    # 应用 archive_details
    archive_details = list(rtoml.loads(archive_details_file.read_text(encoding="utf-8")).values())

    is_replace_same = easy_linput(MESSAGE.D7IAA4, default="N", return_type=str)  == "Y"

    for d in archive_details:
        apply_archive_detail(d, is_replace_same)

    lprint(MESSAGE.R96CC5)



