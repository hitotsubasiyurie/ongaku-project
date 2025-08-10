import sys
import json
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.logger import logger
from src.common.constants import METADATA_PATH, TMP_PATH
from src.metadata_source.musicbrainz_api import MusicBrainzAPI
from src.ongaku_library.basemodels import Album
from src.ongaku_library.ongaku_library import (dump_album_model, album_filename, OngakuLibrary, 
    load_album_model)


BLOCK_SEP = f"\n{'-'*16} seperate {'-'*16}"
I_PREFIX = "I ->         "
Q_PREFIX = "Q ->     "
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

    # TODO : 排除已有 mb 链接的

    # input 输入

    metadata_dir = input(f"Please input metadata directory ({METADATA_PATH}): ").strip("'\"") or METADATA_PATH
    database_dir = input(f"Please input musicbrainz database directory: ").strip("'\"")
    tmp_dir = input(f"Please input temp directory ({TMP_PATH}): ").strip("'\"") or TMP_PATH

    if not metadata_dir or not database_dir or not tmp_dir:
        sys.exit(0)

    cache_dir = os.path.join(tmp_dir, "cache")
    musicbrainz_dir = Path(tmp_dir, "musicbrainz")
    musicbrainz_dir.mkdir(exist_ok=True)

    # 读取元数据文件
    mdfs = OngakuLibrary._scan_metadata_files(metadata_dir)
    albums: list[Album] = list(map(load_album_model, mdfs))

    # 初始化 query list
    qrl_file = os.path.join(tmp_dir, "query_list.log")
    if not os.path.exists(qrl_file):
        query_list = {get_album_identity(a): {} for a in albums}
        dump_query_list_file(qrl_file, query_list)

    # 循环交互

    while True:

        os.system("cls")
        print("请输入动作序号：")
        print("1. 配置 query list file")
        print("2. 搜索 query list file")
        print("3. 应用 query list file")
        action = int(input(""))

        if action == 1:
            mask = input("请输入搜索掩码 (catalognumber, date, album, track_count) (e.g. 1000) : ")
            query_list = load_query_list_file(qrl_file)
            new_query_list = {
                indent: {json.dumps([v if bool(int(mask[i])) else "" for i, v in enumerate(json.loads(indent))], ensure_ascii=False): {}} 
                for indent in query_list.keys()}
            dump_query_list_file(qrl_file, new_query_list)

        elif action == 2:
            api = MusicBrainzAPI(cache_dir=cache_dir, database_dir=database_dir)
            query_list = load_query_list_file(qrl_file)
            for i, _dict1 in query_list.items():
                for q, _dict2 in _dict1.items():
                    if not _dict2:
                        args = [a or None for a in json.loads(q)]
                        albums = api.query_release(*args)
                        [dump_album_model(a, musicbrainz_dir / (album_filename(a)+".json")) for a in albums]
                        _dict2.update({get_album_identity(a): False for a in albums})
                dump_query_list_file(qrl_file, query_list)

        elif action == 3:
            mask = input("请输入应用掩码 (catalognumber, date, album, tracks) (e.g. 0001) : ")
            indent2idx = {get_album_identity(a): i for i, a in enumerate(albums)}
            musicbrainz_ident2album = {get_album_identity(a): a 
                                       for a in list(map(load_album_model, OngakuLibrary._scan_metadata_files(musicbrainz_dir)))}

            query_list = load_query_list_file(qrl_file)
            for i in list(query_list.keys()):
                y_identity = next((r for q, _dict2 in query_list[i].items() for r, y in _dict2.items() if y), None)
                if y_identity:

                    album = albums[indent2idx[i]]
                    musicbrainz_album = musicbrainz_ident2album[y_identity]
                    # 添加 themes, links
                    album.themes = list(sorted(set(album.themes + musicbrainz_album.themes)))
                    album.links.extend(musicbrainz_album.links)

                    # 如果应用，或者原先无值，则更新
                    if bool(int(mask[0])) or not album.catalognumber:
                        album.catalognumber = musicbrainz_album.catalognumber
                    if bool(int(mask[1])) or not album.date:
                        album.date = musicbrainz_album.date
                    if bool(int(mask[2])) or not album.album:
                        album.album = musicbrainz_album.album
                    if bool(int(mask[3])) or not album.tracks:
                        album.tracks = musicbrainz_album.tracks

                    dump_album_model(album, mdfs[indent2idx[i]])
                    query_list.pop(i)
            
            dump_query_list_file(qrl_file, query_list)

