import re
import os
import shutil
import itertools
from pathlib import Path
from functools import cache

from src.utils import read_audio_tags
from src.logger import logger, lprint
from src.basemodels import Album, Track
from src.basemodel_utils import (count_album_similarity, count_track_similarity, album_to_unique_str, 
    track_to_unique_str, albums_assignment, tracks_assignment)
from src.toolkit.message import MESSAGE
from src.toolkit.toolkit_utils import easy_linput, loop_for_actions
from src.toolkit.metadata_source import MusicBrainzDatabase
from src.repository.ongaku_repository import (dump_albums_to_toml, load_albums_from_toml, AUDIO_EXTS, album_filename, 
                                              track_filenames)


SEPERATE = f"{'-'*16} seperate {'-'*16}"

NO_APPLY = "[_NO_APPLY_]"
YES_APPLY = "[_YES_APPLY_]"

ALBUM_SIMILARITY = "ALBUM_SIMILARITY: "
TRACK_SIMILARITY = "TRACK_SIMILARITY: "

OLD_DIRECTORY = "OLD_DIRECTORY: "
NEW_DIRECTORY = "NEW_DIRECTORY: "

RESOURCE_ALBUM = "RESOURCE_ALBUM: "
MATCHING_ALBUM = "MATCHING_ALBUM: "

OLD_AUDIOFILE = "OLD_AUDIOFILE: "
NEW_AUDIOFILE = "NEW_AUDIOFILE: "
RESOURCE_TRACK = "RESOURCE_TRACK: "
MATCHING_TRACK = "MATCHING_TRACK: "


# 缓存
@cache
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
    if match := re.search(r"^\[([0-9.-]+)\]\s+(.+)$", directory.name):
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


def generate_match_log() -> None:

    metadata_file: Path = easy_linput(MESSAGE.QD152EVN, return_type=Path)
    old_parent_dir: Path = easy_linput(MESSAGE.I7EC4HDV, return_type=Path)
    new_parent_dir: Path = easy_linput(MESSAGE.EPNYJ37J, return_type=Path)
    filter_trackcount: bool = easy_linput(MESSAGE.NMN5NFSN, default="Y", return_type=str)  != "N"

    match_log = metadata_file.parent / "match.log"
    content = ""

    theme_albums = load_albums_from_toml(metadata_file)

    # 不嵌套的文件夹 认为是专辑文件夹
    resource_directorys = [d for d in old_parent_dir.rglob("*") 
                           if d.is_dir() 
                           and list(itertools.chain.from_iterable(d.rglob(f"*{ext}") for ext in AUDIO_EXTS))
                           and all(f.is_file() for f in d.glob("*"))]
    
    resource_albums = list(map(analyze_resource_album, resource_directorys))

    for a_row, a_col in zip(*(albums_assignment(resource_albums, theme_albums, filter_trackcount=filter_trackcount)[:2])):

        res_album, res_dir = resource_albums[a_row], resource_directorys[a_row]
        match_album = theme_albums[a_col]

        audios = list(itertools.chain.from_iterable(res_dir.rglob(f"*{ext}") for ext in AUDIO_EXTS))
        res_tracks = list(map(analyze_resource_track, audios))

        row_ind, col_ind, track_similarity, _ = tracks_assignment(res_tracks, match_album.tracks)

        lines = []
        lines.append("")
        lines.append(NO_APPLY)
        lines.append(ALBUM_SIMILARITY + format(count_album_similarity(res_album, match_album), '.2f'))
        lines.append(TRACK_SIMILARITY + format(track_similarity, '.2f'))
        lines.append("")
        lines.append(OLD_DIRECTORY + str(res_dir))
        lines.append(NEW_DIRECTORY + str(new_parent_dir / album_filename(match_album)))
        lines.append("")
        lines.append(RESOURCE_ALBUM + album_to_unique_str(res_album))
        lines.append(MATCHING_ALBUM + album_to_unique_str(match_album))
        lines.append("")
        match_track_names = track_filenames(match_album)
        for row, col in zip(row_ind, col_ind):
            lines.append(OLD_AUDIOFILE + audios[row].name)
            lines.append(NEW_AUDIOFILE + match_track_names[col] + audios[row].suffix.lower())
            lines.append(RESOURCE_TRACK + track_to_unique_str(res_tracks[row]))
            lines.append(MATCHING_TRACK + track_to_unique_str(match_album.tracks[col]))
            lines.append("")

        content += "\n" + SEPERATE + "\n".join(lines) + "\n"
    
    match_log.write_text(content, encoding="utf-8")


def apply_match_log() -> None:
    match_log: Path = easy_linput(MESSAGE.NAWEVS2M, return_type=Path)

    for line in match_log.read_text(encoding="utf-8").split("\n"):
        if line.startswith(SEPERATE):
            apply, old_dir, new_dir, old_file, new_file = [None] * 5
        elif line.startswith(YES_APPLY):
            apply = True
        elif line.startswith(OLD_DIRECTORY):
            old_dir = line.removeprefix(OLD_DIRECTORY)
        elif line.startswith(NEW_DIRECTORY):
            new_dir = line.removeprefix(NEW_DIRECTORY)
            if apply:
                os.makedirs(new_dir, exist_ok=True)
        elif line.startswith(OLD_AUDIOFILE):
            old_file = line.removeprefix(OLD_AUDIOFILE)
        elif line.startswith(NEW_AUDIOFILE):
            new_file = line.removeprefix(NEW_AUDIOFILE)
            if not apply:
                continue
            # 开始应用
            old, new = Path(old_dir, old_file), Path(new_dir, new_file)
            if new.is_file():
                lprint(MESSAGE.HLKQR6TI.format(new))
                old.unlink()
                continue
            if new.suffix.lower() == ".flac" and new.with_suffix(".mp3").exists():
                lprint(MESSAGE.YFH8PA2T.format(new.with_suffix(".mp3")))
                new.with_suffix(".mp3").unlink()
                old.rename(new)
                continue
            if new.suffix.lower() == ".mp3" and new.with_suffix(".flac").exists():
                lprint(MESSAGE.HSUQBJV2.format(new.with_suffix(".flac")))
                old.unlink()
                continue
            old.rename(new)


def clean_old_parent_dir() -> None:
    old_parent_dir: Path = easy_linput(MESSAGE.R2BBVQAA, return_type=Path)

    # 从下往上 删除 没有音频文件的 目录
    for d in reversed(list(filter(Path.is_dir, old_parent_dir.rglob("*")))):
        if not list(itertools.chain.from_iterable(d.rglob(f"*{ext}") for ext in AUDIO_EXTS)):
            shutil.rmtree(d)


def match_resource_and_metadata():

    message2action = {
        MESSAGE.U6RPQN91: generate_match_log,
        MESSAGE.MJVYZVPO: apply_match_log,
        MESSAGE.U6Q2O6NL: clean_old_parent_dir,
        MESSAGE.CLZWFPBZ: None,
    }

    loop_for_actions(message2action)

