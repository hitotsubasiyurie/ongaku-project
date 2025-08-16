import sys
import json
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.logger import logger
from src.common.constants import METADATA_PATH, TMP_PATH
from src.metadata_source.musicbrainz_api import MusicBrainzAPI
from src.metadata_source.musicbrainz_database import MusicBrainzDatabase
from src.basemodels import Album
from src.ongaku_library.ongaku_library import (dump_album_model, album_filename, OngakuScanner, 
    load_album_model)


SEPERATE = f"\n{'-'*16} seperate {'-'*16}\n"
I_PREFIX = f"{' '*0}I{'-'*6}>"
R_PREFIX = f"{' '*4}R{'-'*2}>"
Y_PREFIX = f"{' '*4}Y{'-'*2}>"


def load_query_list_file(filepath: str) -> dict:
    query_list = {}

    for line in Path(filepath).read_text(encoding="utf-8").split("\n"):
        if line.lstrip().startswith(I_PREFIX):
            i = line.split(I_PREFIX)[-1]
            query_list[i] = {}
        elif line.lstrip().startswith(R_PREFIX):
            r = line.split(R_PREFIX)[-1]
            query_list[i][r] = False
        elif line.lstrip().startswith(Y_PREFIX):
            r = line.split(Y_PREFIX)[-1]
            query_list[i][r] = True

    return query_list


def dump_query_list_file(query_list: dict, filepath: str) -> None:
    lines = []
    for i, _dict1 in query_list.items():
        lines.append(I_PREFIX + i)
        for r, y in _dict1.items():
            lines.append((Y_PREFIX if y else R_PREFIX) + r)
        
        lines.append(SEPERATE)

    Path(filepath).write_text("\n".join(lines), encoding="utf-8")


def get_album_id_string(a: Album) -> str:
    return json.dumps([a.catalognumber, a.date, a.album, len(a.tracks)], ensure_ascii=False)


if __name__ == "__main__":

    # input 输入

    metadata_dir = input(f"Please input metadata directory: ").strip("'\"")
    mb_save_dir = input(f"Please input musicbrainz save directory: ").strip("'\"")
    tmp_dir = input(f"Please input temp directory ({TMP_PATH}): ").strip("'\"") or TMP_PATH

    if not metadata_dir or not mb_save_dir or not tmp_dir:
        sys.exit(0)

    cache_dir = os.path.join(tmp_dir, "cache")
    mb_tmp_dir = Path(tmp_dir, "musicbrainz")
    mb_tmp_dir.mkdir(exist_ok=True)

    # 循环交互

    qrl_file = os.path.join(tmp_dir, "query_list.log")
    database = MusicBrainzDatabase()

    while True:

        # 读取元数据文件
        skip_names = [Path(f).name for f in OngakuScanner._scan_metadata_files(mb_save_dir)]
        mdfs = [f for f in OngakuScanner._scan_metadata_files(metadata_dir) if Path(f).name not in skip_names]
        albums: list[Album] = list(map(load_album_model, mdfs))

        os.system("cls")
        print("Please input action number：")
        print("1. Generate query list file")
        print("2. Search query list file")
        print("3. Apply query list file")
        action = int(input(""))

        if action == 1:
            query_list = {get_album_id_string(a): {} for a in albums}
            dump_query_list_file(query_list, qrl_file)


            bin()

            new_query_list = {
                indent: {json.dumps([v if bool(int(mask[i])) else "" for i, v in enumerate(json.loads(indent))], ensure_ascii=False): {}} 
                for indent in query_list.keys()}
            dump_query_list_file(qrl_file, new_query_list)

        elif action == 2:
            query_list = load_query_list_file(qrl_file)
            filter_mask = input("Please input filter mask [catalognumber, date, date_int, track_count] (e.g. 1000) : ")
            order_mask = input("Please input order mask [catalognumber, album, tracks_abstract] (default 111) : ").strip() or "111"

            for i, _dict1 in query_list.items():
                # 跳过已搜索
                if _dict1:
                    continue
                

            api = MusicBrainzAPI(cache_dir=cache_dir, database_dir=database_dir)
            query_list = load_query_list_file(qrl_file)
            for i, _dict1 in query_list.items():
                for q, _dict2 in _dict1.items():
                    if not _dict2:
                        args = [a or None for a in json.loads(q)]
                        albums = api.query_release(*args)
                        [dump_album_model(a, mb_tmp_dir / (album_filename(a)+".json")) for a in albums]
                        _dict2.update({get_album_id_string(a): False for a in albums})
                dump_query_list_file(qrl_file, query_list)

        elif action == 3:
            mask = input("请输入应用掩码 (catalognumber, date, album, tracks) (e.g. 0001) : ")
            indent2idx = {get_album_id_string(a): i for i, a in enumerate(albums)}
            musicbrainz_ident2album = {get_album_id_string(a): a 
                                       for a in list(map(load_album_model, OngakuScanner._scan_metadata_files(mb_tmp_dir)))}

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

