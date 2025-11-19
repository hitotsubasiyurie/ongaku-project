import itertools
import subprocess
from pathlib import Path
from types import SimpleNamespace

import rtoml

from ongaku.core.logger import lprint
from ongaku.core.settings import global_settings
from ongaku.core.kanban import dump_albums_to_toml, load_albums_from_toml
from ongaku.utils.basemodel_utils import album_to_unique_str, albums_assignment, abstract_tracks_info
from ongaku.utils.utils import dump_toml
from ongaku.toolkit.utils import easy_linput


if global_settings.language == "zh":
    PLUGIN_NAME = "合并元数据"
elif global_settings.language == "ja":
    pass
else:
    pass


MESSAGE = SimpleNamespace()


if global_settings.language == "zh":
    MESSAGE.C3X = \
"""
会对专辑列表根据总相似度最大算法，进行一一配对

元数据文件路径：
    如果有多个元数据文件，请使用 | 符号分隔，例如：D:\\Fetch-1.toml | D:\\Fetch-2.toml

link 关键字：
    例如来源关键字是 musicbrainz ，目标关键字是 vgmdb 时
    会过滤 links 中包含 musicbrainz ，不包含 vgmdb 的专辑作为合并来源
    会过滤 links 中包含 vgmdb ，不包含 musicbrainz 的专辑作为合并目标


元数据替换掩码：
    [catalognumber, date, album, tracks]
    例如，掩码 0001 代表只替换目标的 tracks 信息
    例如，掩码 0000 代表不替换任何信息，只是附加至 link
"""
    MESSAGE.XX1 = "请输入一个或多个元数据文件路径："
    MESSAGE.OG9 = "请输入作为来源的专辑的 link 的关键词："
    MESSAGE.K98 = "请输入合并目标的专辑的 link 的关键词："
    MESSAGE.LP9 = "请至少输入一个 link 关键词。"
    MESSAGE.C99 = "合并时是否来源与目标专辑的 catalognumber 必须相同（Y/N）（默认N）："
    MESSAGE.D7I = "合并时是否来源与目标专辑的 tracks 数量必须相同（Y/N）（默认Y）："
    MESSAGE.D99 = "请修改合并详细文件：{}"
    MESSAGE.SRH = "请决定是否应用合并（Y/N）（默认N）："
    MESSAGE.SRE = "请输入来源合并至目标的元数据替换掩码（例如 0001）："
    MESSAGE.GGG = "元数据替换掩码格式不正确。"
    MESSAGE.CS5 = "合并时是否允许自动替换目标中的空值（Y/N）（默认Y）："
    MESSAGE.S75 = "合并详细文件被不正确的编辑。"
    MESSAGE.DD4 = "合并元数据成功。"
elif global_settings.language == "ja":
    pass
else:
    pass


IS_APPLY = "IS_APPLY"
SIMILARITY = "SIMILARITY"
SRC_ALBUM = "SRC_ALBUM"
DST_ALBUM = "DST_ALBUM"
SRC_TRACKS = "SRC_TRACKS"
DST_TRACKS = "DST_TRACKS"


def main():

    lprint(MESSAGE.C3X)

    file_str = easy_linput(MESSAGE.XX1, return_type=str)
    metadata_files = list(map(Path, [s.strip().strip("'\"") for s in file_str.split("|")]))

    src_ky = easy_linput(MESSAGE.OG9, default="", return_type=str)
    dst_ky = easy_linput(MESSAGE.K98, default="", return_type=str)

    if not src_ky and not dst_ky:
        lprint(MESSAGE.LP9)
        return

    filter_catno = easy_linput(MESSAGE.C99, default="N", return_type=str) == "Y"
    filter_trackcount = easy_linput(MESSAGE.D7I, default="Y", return_type=str) != "N"

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
    merge_details_file = Path(global_settings.temp_directory, "merge_details.toml")

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

    subprocess.run(f'explorer /select,"{merge_details_file}"')

    # 用户编辑 merge_details
    lprint(MESSAGE.D99.format(merge_details_file))
    _continue = easy_linput(MESSAGE.SRH, default="N", return_type=str)  == "Y"
    if not _continue:
        return

    # 应用 merge_details
    merge_details = list(rtoml.loads(merge_details_file.read_text(encoding="utf-8")).values())

    replace_mask = easy_linput(MESSAGE.SRE)
    if not len(replace_mask) == 4 and set(replace_mask).issubset({"0", "1"}):
        lprint(MESSAGE.GGG)
        return
    
    replace_blank = easy_linput(MESSAGE.CS5, default="Y", return_type=str)  != "N"

    remove_srcs = set()

    for row, col, d in zip(row_ind, col_ind, merge_details):

        # 检查编辑
        if d[SRC_ALBUM] != src_unique_strs[row] or d[DST_ALBUM] != dst_unique_strs[col]:
            lprint(MESSAGE.S75)
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

    lprint(MESSAGE.DD4)

