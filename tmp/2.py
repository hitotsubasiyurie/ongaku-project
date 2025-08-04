import sys
import json
import pickle
import os
import itertools
from pathlib import Path
from collections import defaultdict

sys.path.append(r"E:\my\ongaku")
os.environ["ONGAKU_TMP_PATH"] = r"E:\ongaku-tmp"


from ongaku.logger import logger
from ongaku.metadata.vgmdb_api import VGMdbAPI
from ongaku.metadata.musicbrainz_api import MusicBrainzAPI
from ongaku.common.metadata import Album, metadata_filename, save_metadata, load_metadata


BLOCK_SEP = f"\n{'-'*16} seperate {'-'*16}"
I_PREFIX = "I -> "
Q_PREFIX = "Q -> "
R_PREFIX = "R -> "
YR_PREFIX = "YR -> "


def load_query_list_file(filepath: str) -> dict:
    query_list = {}

    for line in Path(filepath).read_text(encoding="utf-8").split("\n"):
        if line.lstrip().startswith(I_PREFIX):
            i = line.split(I_PREFIX)[-1]
            query_list[i] = {}
        elif line.lstrip().startswith(Q_PREFIX):
            q = line.split(Q_PREFIX)[-1]
            query_list[i][q] = {}
        elif line.lstrip().startswith(R_PREFIX):
            r = line.split(R_PREFIX)[-1]
            query_list[i][q][r] = False
        elif line.lstrip().startswith(YR_PREFIX):
            r = line.split(YR_PREFIX)[-1]
            query_list[i][q][r] = True

    return query_list


def dump_query_list_file(filepath: str, query_list: dict) -> None:
    lines = []
    for i, _dict1 in query_list.items():
        lines.append(I_PREFIX + i)
        for q, _dict2 in _dict1.items():
            lines.append(" "*4 + Q_PREFIX + q)
            for r, y in _dict2.items():
                lines.append(" "*8 + (R_PREFIX if not y else YR_PREFIX) + r)
        
        lines.append(BLOCK_SEP)

    Path(filepath).write_text("\n".join(lines), encoding="utf-8")


def get_album_identity(a: Album) -> str:
    return json.dumps([a.catalognumber, a.date, a.album, len(a.tracks)], ensure_ascii=False)


if __name__ == "__main__":
    vgmdb_dir = Path(r"E:\ongaku-tmp\vgmdb")
    mb_dir = Path(r"E:\ongaku-tmp\musicbrainz")
    result_dir = Path(r"E:\ongaku-tmp\result")

    album_db = Path(r"D:\mb\album")

    qrl_file = r"E:\ongaku-tmp\query_list.log"


    # vgmdb 文件夹 -> query_list.log
    # vgmdb_albums = list(map(load_metadata, vgmdb_dir.rglob("*.json")))
    # query_list = {
    #     get_album_identity(a): {
    #         # json.dumps([a.catalognumber, a.date, a.album, len(a.tracks)], ensure_ascii=False): {},
    #         # json.dumps([a.catalognumber, "", a.album, len(a.tracks)], ensure_ascii=False): {},
    #         # json.dumps([a.catalognumber, a.date, "", len(a.tracks)], ensure_ascii=False): {},
    #         json.dumps(["", "", a.album, len(a.tracks)], ensure_ascii=False): {},
    #     }
    #     for a in vgmdb_albums
    # }
    # dump_query_list_file(qrl_file, query_list)

    # query_list.log -> musicbrainz 文件夹
    api = MusicBrainzAPI(cache_dir=r"E:\ongaku-tmp\cache", album_db=r"D:\MusicBrainzDatabse\album")
    query_list = load_query_list_file(qrl_file)
    for i, _dict1 in query_list.items():
        for q, _dict2 in _dict1.items():
            if not _dict2:
                args = [a or None for a in json.loads(q)]
                albums = api.query_release(*args)
                [save_metadata(a, mb_dir / metadata_filename(a)) for a in albums]
                _dict2.update({get_album_identity(a): False for a in albums})
        dump_query_list_file(qrl_file, query_list)

    # vgmdb 文件夹 + musicbrainz 文件夹 -> result 文件夹
    vgmdb_ident_map = {get_album_identity(a): a for a in list(map(load_metadata, vgmdb_dir.rglob("*.json")))}
    mb_ident_map = {get_album_identity(a): a for a in list(map(load_metadata, mb_dir.rglob("*.json")))}

    query_list = load_query_list_file(qrl_file)
    for i in list(query_list.keys()):
        y_identity = next((r for q, _dict2 in query_list[i].items() for r, y in _dict2.items() if y), None)
        if y_identity:
            mb_ident_map[y_identity].themes.extend(vgmdb_ident_map[i].themes)
            mb_ident_map[y_identity].links.extend(vgmdb_ident_map[i].links)
            album = mb_ident_map[y_identity]
            save_metadata(album, result_dir / metadata_filename(album))
            query_list.pop(i)
            (vgmdb_dir / metadata_filename(vgmdb_ident_map[i])).unlink()
    dump_query_list_file(qrl_file, query_list)

