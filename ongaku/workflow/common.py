import re
import itertools
from pathlib import Path

from ongaku.core.constants import AUDIO_EXTS
from ongaku.utils.utils import read_audio_tags
from ongaku.core.basemodels import Album, Track


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


