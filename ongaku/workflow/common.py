import re
import itertools
from pathlib import Path
from typing import Any, Type, Callable, TypeVar

import orjson
from numpy import asarray
from tqdm import tqdm
from rapidfuzz import fuzz
from scipy.optimize import linear_sum_assignment

from ongaku.core.constants import AUDIO_EXTS
from ongaku.core.logger import linput, lprint, logger
from ongaku.core.settings import  global_settings
from ongaku.utils import read_audio_tags
from ongaku.core.basemodels import Album, Track


_T = TypeVar("T")


def easy_linput(prompt: object  = "", default: Any = None, return_type: Type[_T] = str) -> _T:
    """
    :param default: 默认为 None 时，会循环提示输入
    :param return_type: 返回结果类型
    """

    if default is not None and not isinstance(default, return_type):
        raise TypeError(f"Default value invalid. Expecting type {return_type.__name__}")

    while True:
        val = linput(prompt)
        if not val:
            if default is None:
                continue
            return default
        else:
            try:
                if return_type == Path:
                    val = Path(val.strip("'\""))
                else:
                    val = return_type(val)
                return val
            except Exception:
                continue


def loop_for_actions(message2action: dict[str, Callable]) -> None:
    messages, actions = list(message2action.keys()), list(message2action.values())
    while True:
        lprint("\n".join(f"{i+1}. {m}" for i, m in enumerate(messages)) + "\n")
        number = easy_linput("?: ", return_type=int)
        lprint()

        if not (0 <= number - 1 <= len(messages)):
            continue

        try:
            lprint(f"{'-'*8} {messages[number - 1]} {'-'*8}")
            func = actions[number - 1]
            if not func:
                return
            func()
            lprint("-"*32)
        except Exception as e:
            lprint(f"Error: {e}")
            logger.error("", exc_info=1)


def album_to_unique_str(a: Album) -> str:
    return orjson.dumps([a.catalognumber, a.date, a.album, len(a.tracks)]).decode("utf-8").replace('"', "'")


def track_to_unique_str(t: Track) -> str:
    return orjson.dumps([t.tracknumber, t.title, t.artist]).decode("utf-8").replace('"', "'")


def abstract_tracks_info(album: Album) -> str:
    """
    摘要 tracks 信息。
    """
    return "\n".join(f"{t.tracknumber}. {t.title}" for t in album.tracks)


def count_track_similarity(a: Track, b: Track) -> float:
    """
    计算两个 Track 的相似度。\n
    :return ratio: 相似度，0 ~ 100
    """
    ratio = fuzz.ratio(f"{a.tracknumber}. {a.title}", f"{b.tracknumber}. {b.title}")
    # 均有 artist 信息时才比较
    if a.artist and b.artist:
        ratio += fuzz.ratio(a.artist, b.artist)
        return ratio / 2
    return ratio


def count_album_similarity(a: Album, b: Album) -> float:
    """
    计算两个 Album 的相似度。\n
    :return ratio: 相似度，0 ~ 100
    """
    if abs(len(a.tracks) - len(b.tracks)) == 0:
        trackcount_sim = 100
    elif abs(len(a.tracks) - len(b.tracks)) <= 3:
        trackcount_sim = 80
    elif abs(len(a.tracks) - len(b.tracks)) <= 5:
        trackcount_sim = 60
    else:
        trackcount_sim = 0
    ratio = (fuzz.ratio(a.catalognumber, b.catalognumber) + 
             fuzz.ratio(a.date, b.date) + 
             fuzz.ratio(a.album, b.album) + 
             fuzz.ratio(abstract_tracks_info(a), abstract_tracks_info(b)) + 
             trackcount_sim)
    ratio = ratio / 5
    return ratio


def albums_assignment(row_albums: list[Album], col_albums: list[Album], 
                      filter_catno: bool = False, filter_trackcount: bool = False
                      ) -> tuple[list[int], list[int], float, list[list[float]]]:
    """
    Album 模型 总相似度最大分配。会 print 进度条。\n
        c1 c2 c3 ... cm
    r1  
    r2  
    ...  
    rn  
    \n
    :param row_albums: 行 Album 模型列表
    :param col_albums: 列 Album 模型列表
    :param filter_catno: 是否过滤 catno 相同
    :param filter_trackcount: 是否过滤 tracks 数量相同
    :returns row_ind, col_ind, aver_similarity, sim_matrix: 
    """
    if not row_albums or not col_albums:
        return [], [], 0, []
    
    sim_matrix = asarray([[0] * len(col_albums) for _ in range(len(row_albums))])

    for i, ra in enumerate(tqdm(row_albums, desc="Count albums similarity", miniters=0)):
        for j, ca in enumerate(col_albums):

            if filter_catno and ra.catalognumber != ca.catalognumber:
                continue
            if filter_trackcount and len(ra.tracks) != len(ca.tracks):
                continue

            sim_matrix[i, j] = count_album_similarity(ra, ca)

    row_ind, col_ind = linear_sum_assignment(sim_matrix, maximize=True)

    # 按相似度 倒排
    pairs = sorted(zip(row_ind, col_ind, sim_matrix[row_ind, col_ind]), 
                   key=lambda x: x[2],
                   reverse=True)
    row_ind, col_ind, _ = map(asarray, zip(*pairs))

    aver_similarity = sim_matrix[row_ind, col_ind].sum() / len(row_ind)

    return row_ind, col_ind, aver_similarity, sim_matrix


def tracks_assignment(row_tracks: list[Track], col_tracks: list[Track]
                      ) -> tuple[list[int], list[int], float, list[list[float]]]:
    """
    Track 模型 总相似度最大分配。\n
    :param row_tracks: 行 Track 模型列表
    :param col_tracks: 列 Track 模型列表
    :returns row_ind, col_ind, aver_similarity, sim_matrix: 
    """
    if not row_tracks or not col_tracks:
        return [], [], 0, []
    
    sim_matrix = [[count_track_similarity(rt, ct) for ct in col_tracks] 
                    for rt in row_tracks]
    sim_matrix = asarray(sim_matrix)
    row_ind, col_ind = linear_sum_assignment(sim_matrix, maximize=True)
    aver_similarity = sim_matrix[row_ind, col_ind].sum() / len(row_ind)
    return row_ind, col_ind, aver_similarity, sim_matrix


# "04. 戦車、乗ります!.flac", "04 - 戦車、乗ります!.flac"
_TRACK_PAT_1 = re.compile(r"^(\d+)\s*[.-]\s*(.+)$")


def analyze_track(track_file: str | Path) -> Track | None:
    track_file = Path(track_file)

    if not track_file.is_file():
        return

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

# 按优先级排序
# "[ANZX-6810] [2012-02-23] PERFECT IDOL 03 [4]"
_ALBUM_PAT_1 = re.compile(r"^\[([A-Za-z0-9-]+)\]\s*\[([0-9.-]{4,10})\]\s*(.+)$")
# "[2021-01-02] SPCD Drama (flac)"
_ALBUM_PAT_2 = re.compile(r"^\[([0-9.-]{4,10})\]\s*(.+)$")
# "プリパラ プロミス! リズム! パラダイス! [210102]"
_ALBUM_PAT_3 = re.compile(r"^(.+)\[([0-9]{6})\]$")
# "[190911]プリパラ プロミス! リズム! パラダイス![320K]"
_ALBUM_PAT_4 = re.compile(r"^\[([0-9]{6})\](.+)$")
# "2007.09.27 Mayumi Gojo - Iridescent+"
_ALBUM_PAT_5 = re.compile(r"^([0-9.-]{4,10})\s*(.+)$")


def analyze_album(album_dir: str | Path) -> Album | None:
    """
    :param directory: 扁平的专辑目录。仅分析它的表层音频文件
    """
    album_dir = Path(album_dir)

    if not album_dir.is_dir():
        return

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
    if match := _ALBUM_PAT_4.search(album_dir.name):
        if not date: 
            d = match.group(1)
            date = f"20{d[:2]}-{d[2:4]}-{d[4:6]}"
        if not album: album = match.group(2)
    if match := _ALBUM_PAT_5.search(album_dir.name):
        if not date or len(date) < len(match.group(1)): date = match.group(1)
        if not album: album = match.group(2)
    
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


