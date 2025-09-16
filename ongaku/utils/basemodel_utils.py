import orjson
from numpy import ndarray, zeros, asarray, float32
from tqdm import tqdm
from rapidfuzz import fuzz
from scipy.optimize import linear_sum_assignment

from ongaku.core.basemodels import Album, Track


def album_to_unique_str(a: Album) -> str:
    return orjson.dumps([a.catalognumber, a.date, a.album, len(a.tracks)]).decode("utf-8")


def track_to_unique_str(t: Track) -> str:
    return orjson.dumps([t.tracknumber, t.title, t.artist]).decode("utf-8")


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
                      ) -> tuple[list[int], list[int], float, ndarray]:
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
    sim_matrix = zeros((len(row_albums), len(col_albums)), dtype=float32)

    for i, ra in enumerate(tqdm(row_albums, desc="Count albums similarity", miniters=0)):

        for j, ca in enumerate(col_albums):
            if ((not filter_catno or ra.catalognumber == ca.catalognumber) 
                and (not filter_trackcount or len(ra.tracks) == len(ca.tracks))):
                sim_matrix[i, j] = count_album_similarity(ra, ca)

    row_ind, col_ind = linear_sum_assignment(sim_matrix, maximize=True)
    aver_similarity = sim_matrix[row_ind, col_ind].sum() / len(row_ind)

    return row_ind, col_ind, aver_similarity, sim_matrix


def tracks_assignment(row_tracks: list[Track], col_tracks: list[Track]
                      ) -> tuple[list[int], list[int], float, ndarray]:
    """
    Track 模型 总相似度最大分配。\n
    :param row_tracks: 行 Track 模型列表
    :param col_tracks: 列 Track 模型列表
    :returns row_ind, col_ind, aver_similarity, sim_matrix: 
    """
    sim_matrix = [[count_track_similarity(rt, ct) for ct in col_tracks] 
                    for rt in row_tracks]
    sim_matrix = asarray(sim_matrix)
    row_ind, col_ind = linear_sum_assignment(sim_matrix, maximize=True)
    aver_similarity = sim_matrix[row_ind, col_ind].sum() / len(row_ind)
    return row_ind, col_ind, aver_similarity, sim_matrix

