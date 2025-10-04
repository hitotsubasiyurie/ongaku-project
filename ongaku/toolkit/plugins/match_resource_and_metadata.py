import re
import os
import shutil
import itertools
from pathlib import Path

from ongaku.logger import logger, lprint
from ongaku.basemodel_utils import (count_album_similarity, count_track_similarity, album_to_unique_str, 
    track_to_unique_str, albums_assignment, tracks_assignment)
from ongaku.toolkit.message import MESSAGE
from ongaku.toolkit.toolkit_utils import easy_linput, loop_for_actions
from ongaku.repository_utils import load_albums_from_toml, album_filename, track_filenames
from ongaku.audiofile_utils import analyze_resource_album, analyze_resource_track


AUDIO_EXTS = {".mp3", ".flac"}

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

