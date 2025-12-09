from collections import Counter

from src.core.logger import logger
from src.core.basemodels import Album, Disc


def assemble_albums_from_discs(catnos: list[str], date: str, album_title: str, discs: list[Disc], link: str) -> list[Album]:
    """
    | catno | discs | Album |   | |
    |-------|-------|-------|---|-|
    | 0     | 0     | 1     |   | 1 张专辑，无 catno 无 tracks |
    | 0     | 1     | 1     |   | 1 张专辑，无 catno |
    | 0     | n     | n     |   | n 张专辑，无 catno |
    | 1     | 0     | 1     |   | 1 张专辑，无 tracks |
    | 1     | 1     | 1     |   | 1 张专辑 |
    | 1     | n     | n     |   | n 张专辑 |
    | n     | 0     | n     |   | n 张专辑，无 tracks |
    | n     | 1     | 1     | × | 1 张专辑，无法确定 catno |
    | n     | n     | n     |   | n 张专辑 |
    | n     | n < m | m     | × | m 张专辑，无法确定 catno |
    | n     | n > m | n     | × | m 张专辑，无法确定 catno |
    """
    if len(catnos) <= 1 and len(discs) <= 1:
        albums = [Album(catalognumber=catnos[0] if catnos else "", date=date, album=album_title,
                                tracks=discs[0].tracks if discs else [], links=[link])]
    elif len(catnos) <= 1:
        albums = [Album(catalognumber=catnos[0] if catnos else "", date=date,
                                    album=f"{album_title} {d.disc}", tracks=d.tracks, links=[link])
                    for d in discs]
    elif len(discs) == 0:
        albums = [Album(catalognumber=c, date=date, album=album_title, tracks=[], links=[link]) for c in catnos]
    elif len(catnos) == len(discs):
        albums = [Album(catalognumber=c, date=date, album=f"{album_title} {d.disc}", tracks=d.tracks, links=[link])
                    for c, d in zip(catnos, discs)]
    else:
        logger.warning(f"Failed to assign albums. {catnos, date, album_title}")
        albums = [Album(catalognumber=", ".join(catnos), date=date, album=f"{album_title} {d.disc}", 
                        tracks=d.tracks, links=[link])
                    for d in discs]
    
    # 处理同名专辑
    _count = Counter([a.album for a in albums])
    for i, a in enumerate(albums):
        if _count[a.album] > 1:
            a.album += f" Disc {i+1}"

    logger.info(f"Got {len(albums)} albums. {[(a.catalognumber, a.album) for a in albums]}")
    return albums



