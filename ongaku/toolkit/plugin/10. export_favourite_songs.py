import itertools
import shutil
from pathlib import Path
from types import SimpleNamespace

import rtoml

from ongaku.core.logger import lprint
from ongaku.core.settings import global_settings
from ongaku.core.kanban import KanBan
from ongaku.core.constants import AUDIO_EXTS
from ongaku.core.basemodels import Album, Track
from ongaku.utils.basemodel_utils import (album_to_unique_str, track_to_unique_str, 
    albums_assignment, tracks_assignment)
from ongaku.toolkit.toolkit_utils import easy_linput
from ongaku.utils.audiofile_utils import analyze_resource_album, analyze_resource_track
from ongaku.utils.utils import dump_toml


if global_settings.language == "zh":
    PLUGIN_NAME = "导出喜欢的歌曲"
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


def is_audio_same(file1: str, file2: str) -> bool:
    pass


def export_track(src_file: str, dst_dir: str, album: Album, track: Track) -> None:
    dst_file = Path(dst_dir, Path(src_file).name)
    shutil.copy2(src_file, dst_file)


def main() -> None:
    kanban = KanBan(global_settings.metadata_directory, global_settings.resource_directory)
    
    for theme_kanban in kanban.theme_kanbans:
        for album_kanban in theme_kanban.album_kanbans:
            pass







