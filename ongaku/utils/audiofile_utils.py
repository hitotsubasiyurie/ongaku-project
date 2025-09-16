import re
import itertools
from pathlib import Path

from ongaku.utils.utils import read_audio_tags
from ongaku.core.basemodels import Album, Track


def analyze_resource_track(audio: str) -> Track:
    audio = Path(audio)

    tags = read_audio_tags(audio)
    tracknumber, title, artist = [tags[k] or "" for k in ["tracknumber", "title", "artist"]]

    if not all([tracknumber.isdigit(), title]):
        if match := re.search(r"^(\d+)\s*[.-]\s*(.+)$", audio.stem):
            # 空字符 或 包含其他非数字
            if not tracknumber.isdigit(): tracknumber = match.group(1)
            if not title: title = match.group(2)
    
    tracknumber = int(tracknumber) if tracknumber.isdigit() else None
    if not title: title = audio.name
    
    return Track(tracknumber=tracknumber, title=title, artist=artist)


def analyze_resource_album(directory: str) -> Album:
    """
    :param directory: 扁平专辑目录
    """
    directory = Path(directory)
    audios = list(itertools.chain.from_iterable(directory.rglob(f"*{ext}") for ext in AUDIO_EXTS))

    tags = read_audio_tags(audios[0])
    catalognumber, date, album = [tags[k] or "" for k in ["catalognumber", "date", "album"]]
    
    # 匹配 [COCX-1052] [2021-01-02] xxx
    if match := re.search(r"^\[([A-Z0-9-]+)\]\s+\[([0-9.-]+)\]\s+(.+)$", directory.name):
        if not catalognumber: catalognumber = match.group(1)
        if not date or len(date) < len(match.group(2)): date = match.group(2)
        if not album: album = match.group(3)
    # 匹配 [2021-01-02] xxx
    if match := re.search(r"^\[*([0-9.-]+)\]*\s+(.+)$", directory.name):
        if not date or len(date) < len(match.group(1)): date = match.group(1)
        if not album: album = match.group(2)
    # 匹配 xxx [210102]
    if match := re.search(r"^(.+)\[([0-9]{6})\]$", directory.name):
        if not date: 
            d = match.group(2)
            date = f"20{d[:2]}-{d[2:4]}-{d[4:6]}"
        if not album: album = match.group(1)
    if not album: album = directory.name

    # date 字段替换常见字符
    date = re.sub(r"[./]", "-", date)
    try:
        album_model = Album(catalognumber=catalognumber, date=date, album=album, 
                            tracks=list(sorted([analyze_resource_track(a) for a in audios], key=lambda a: a.tracknumber)))
    except Exception:
        album_model = Album(catalognumber=catalognumber, date="", album=album, 
                            tracks=list(sorted([analyze_resource_track(a) for a in audios], key=lambda a: a.tracknumber)))
    return album_model
