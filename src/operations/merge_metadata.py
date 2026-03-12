import itertools
from pathlib import Path

import rtoml

from src.core.console import cprint, easy_cinput
from src.core.i18n import g_message
from src.core.settings import g_settings
from src.core.storage import dump_albums_to_toml, load_albums_from_toml
from src.operations._common import album_to_unique_str, albums_assignment, abstract_tracks_info
from src.utils import dump_toml

OPERATION_TITLE = g_message.WF_20251204_195020


IS_APPLY = "IS_APPLY"
SIMILARITY = "SIMILARITY"
SRC_ALBUM = "SRC_ALBUM"
DST_ALBUM = "DST_ALBUM"
SRC_TRACKS = "SRC_TRACKS"
DST_TRACKS = "DST_TRACKS"


def merge_metadata():
    cprint(g_message.WF_20251204_195021)

    file_str = easy_cinput(g_message.WF_20251204_195022, return_type=str)
    metadata_files = list(map(Path, [s.strip().strip("'\"") for s in file_str.split("|")]))

    src_ky = easy_cinput(g_message.WF_20251204_195023, default="", return_type=str)
    dst_ky = easy_cinput(g_message.WF_20251204_195024, default="", return_type=str)

    if not src_ky and not dst_ky:
        cprint(g_message.WF_20251204_195025)
        return

    filter_catno = easy_cinput(g_message.WF_20251204_195026, default="N", return_type=str) == "Y"
    filter_trackcount = easy_cinput(g_message.WF_20251204_195027, default="Y", return_type=str) == "Y"

    files_albums = list(map(load_albums_from_toml, metadata_files))

    # 分出 来源和目标 专辑模型
    src_albums, dst_albums = [], []
    for a in itertools.chain.from_iterable(files_albums):
        text = "//".join(a.links)
        # 过滤 反过滤
        if src_ky in text and not (dst_ky and dst_ky in text):
            src_albums.append(a)
        elif dst_ky in text and not (src_ky and src_ky in text):
            dst_albums.append(a)

    src_unique_strs, dst_unique_strs = list(map(album_to_unique_str, src_albums)), list(map(album_to_unique_str, dst_albums))
    src_track_infos, dst_track_infos = list(map(abstract_tracks_info, src_albums)), list(map(abstract_tracks_info, dst_albums))

    merge_details = []
    merge_details_file = Path(g_settings.TMP_DIRECTORY, "merge_details.toml")

    # 生成 merge_details
    row_ind, col_ind, _, sim_matrix = albums_assignment(src_albums, dst_albums, filter_catno, filter_trackcount)

    for row, col in zip(row_ind, col_ind):
        d = {}
        d[IS_APPLY] = False
        d[SIMILARITY] = format(sim_matrix[row][col], '.2f')
        d[SRC_ALBUM] = src_unique_strs[row]
        d[DST_ALBUM] = dst_unique_strs[col]
        d[SRC_TRACKS] = src_track_infos[row]
        d[DST_TRACKS] = dst_track_infos[col]
        merge_details.append(d)

    dump_toml({str(i+1): d for i, d in enumerate(merge_details)}, merge_details_file)

    # 用户编辑 merge_details
    cprint(g_message.WF_20251204_195028.format(merge_details_file))
    if not easy_cinput(g_message.WF_20251204_195029, default="N", return_type=str)  == "Y":
        return

    # 应用 merge_details
    merge_details = list(rtoml.loads(merge_details_file.read_text(encoding="utf-8")).values())

    replace_mask = easy_cinput(g_message.WF_20251204_195030)
    if not len(replace_mask) == 4 and set(replace_mask).issubset({"0", "1"}):
        cprint(g_message.WF_20251204_195031)
        return
    
    replace_blank = easy_cinput(g_message.WF_20251204_195032, default="Y", return_type=str)  == "Y"

    remove_srcs = set()

    for row, col, d in zip(row_ind, col_ind, merge_details):

        # 检查编辑
        if d[SRC_ALBUM] != src_unique_strs[row] or d[DST_ALBUM] != dst_unique_strs[col]:
            cprint(g_message.WF_20251204_195033)
            return
        
        if not d[IS_APPLY]:
            continue

        src, dst = src_albums[row], dst_albums[col]
        for b, field in zip(replace_mask, ["catalognumber", "date", "album", "tracks"]):
            if (int(b) and getattr(src, field)) or (replace_blank and not getattr(dst, field)):
                setattr(dst, field, getattr(src, field))

            dst.links = dst.links + src.links

            remove_srcs.add(src)

    # 保存文件
    for file, albums in zip(metadata_files, files_albums):
        albums = list(itertools.filterfalse(remove_srcs.__contains__, albums))
        dump_albums_to_toml(albums, file)

    cprint(g_message.WF_20251204_195034)

