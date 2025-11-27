import re
import json
import shutil
import itertools
from collections import defaultdict
from pathlib import Path

from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.id3 import ID3

from ongaku.core.logger import lprint, logger
from ongaku.core.settings import global_settings
from ongaku.core.kanban import KanBan, track_filenames, load_albums_from_toml, dump_albums_to_toml
from ongaku.core.constants import AUDIO_EXTS
from ongaku.core.basemodels import Album, Track
from ongaku.toolkit.utils import easy_linput
from ongaku.utils.utils import write_audio_tags, read_audio_tags
from ongaku.external import show_audio_stream_info, compress_image


if global_settings.language == "zh":
    PLUGIN_NAME = "从本地音频获取专辑元数据"
    class MESSAGE:
        OLI4J5 = """
保存路径：
    若是文件夹，将会在其下生成新的元数据文件。
    若是已有的元数据文件路径，将会追加它未包含的专辑元数据

音频资源父目录：
    
    """
        SOPLP0 = "请输入保存路径："
        DFT895 = "请输入音频资源父目录："
        RE5LKM = "解析完成。没有获得专辑元数据。"
        GFD8P9 = "解析完成。获得 {} 个专辑元数据，是否保存至 {} （Y/N）（默认Y）："
        IOP596 = "保存完成。"
elif global_settings.language == "ja":
    pass
else:
    pass


################ 工具函数 ################

# "04. 戦車、乗ります!.flac", "04 - 戦車、乗ります!.flac"
_TRACK_PAT_1 = re.compile(r"^(\d+)\s*[.-]\s*(.+)$")

def analyze_track(track_file: str | Path) -> Track:
    track_file = Path(track_file)

    tags = read_audio_tags(str(track_file))
    tracknumber, title, artist = [tags[k] for k in ["tracknumber", "title", "artist"]]

    if tracknumber.isdigit() and title:
        return Track(tracknumber=int(tracknumber), title=title, artist=artist)

    # 优先使用音频元数据
    if match := _TRACK_PAT_1.search(track_file.stem):
        if not tracknumber.isdigit(): tracknumber = match.group(1)
        if not title: title = match.group(2)
    
    tracknumber = int(tracknumber) if tracknumber.isdigit() else None
    if not title: title = track_file.name
    
    return Track(tracknumber=tracknumber, title=title, artist=artist)


# "[ANZX-6810] [2012-02-23] PERFECT IDOL 03 [4]", "[ANZX-6810] [2012.02.23] PERFECT IDOL 03 [4]"
_ALBUM_PAT_1 = re.compile(r"^\[([A-Za-z0-9-]+)\]\s+\[([0-9.-]+)\]\s+(.+)$")
# [2021-01-02] xxx
_ALBUM_PAT_2 = re.compile(r"^\[*([0-9.-]+)\]*\s+(.+)$")
# xxx [210102]
_ALBUM_PAT_3 = re.compile(r"^(.+)\[([0-9]{6})\]$")

def analyze_album(album_dir: str | Path) -> Album | None:
    """
    :param directory: 扁平专辑目录
    """
    album_dir = Path(album_dir)
    # 仅分析表层音频
    audios = list(itertools.chain.from_iterable(album_dir.glob(f"*{ext}") for ext in AUDIO_EXTS))

    if not audios:
        return

    tags = read_audio_tags(audios[0])
    catalognumber, date, album = [tags[k] for k in ["catalognumber", "date", "album"]]
    
    if match := _ALBUM_PAT_1.search(album_dir.name):
        if not catalognumber: catalognumber = match.group(1)
        if not date or len(date) < len(match.group(2)): date = match.group(2)
        if not album: album = match.group(3)
    if match := _ALBUM_PAT_2.search(album_dir.name):
        if not date or len(date) < len(match.group(1)): date = match.group(1)
        if not album: album = match.group(2)
    if match := _ALBUM_PAT_3.search(album_dir.name):
        if not date: 
            d = match.group(2)
            date = f"20{d[:2]}-{d[2:4]}-{d[4:6]}"
        if not album: album = match.group(1)
    if not album: album = album_dir.name

    # date 字段替换常见字符
    date = re.sub(r"[./]", "-", date)
    try:
        album_model = Album(catalognumber=catalognumber, date=date, album=album, 
                            tracks=list(sorted([analyze_track(a) for a in audios], key=lambda a: a.tracknumber)))
    except Exception:
        album_model = Album(catalognumber=catalognumber, date="", album=album, 
                            tracks=list(sorted([analyze_track(a) for a in audios], key=lambda a: a.tracknumber)))
    return album_model


################ 主函数 ################

def main() -> None:
    lprint(MESSAGE.OLI4J5)

    metadata_file = easy_linput(MESSAGE.SOPLP0, return_type=Path)
    resource_directory = easy_linput(MESSAGE.DFT895, return_type=Path)

    # 扁平、存在音频 的目录 认为是专辑目录
    album_dirs = [d for d in resource_directory.rglob("*") 
                if d.is_dir() 
                and all(f.is_file() for f in d.glob("*"))
                and list(itertools.chain.from_iterable(d.glob(f"*{ext}") for ext in AUDIO_EXTS))]

    albums = list(map(analyze_album, album_dirs))

    if not albums:
        lprint(MESSAGE.RE5LKM)
        return

    if not easy_linput(MESSAGE.GFD8P9.format(len(albums), metadata_file), default="Y", return_type=str)  == "Y":
        return

    dump_albums_to_toml(load_albums_from_toml(metadata_file) + albums, metadata_file)
    lprint(MESSAGE.IOP596)




















