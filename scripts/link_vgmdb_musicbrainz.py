import sys
import json
import os
import itertools
from typing import Generator
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.logger import logger
from src.common.constants import METADATA_PATH, TMP_PATH
from src.metadata_source.musicbrainz_api import MusicBrainzAPI
from src.metadata_source.musicbrainz_database import MusicBrainzDatabase
from src.common.basemodels import Album
from src.ongaku_library.ongaku_library import (dump_album_model, album_filename, OngakuScanner, 
    load_album_model)

# TODO: link.json 格式


SEPERATE = f"\n{'-'*16} seperate {'-'*16}\n"
V_PREFIX = f"{' '*0}V{'-'*6}>"
M_PREFIX = f"{' '*4}M{'-'*2}>"
Y_PREFIX = f"{' '*4}Y{'-'*2}>"


def load_query_list_file(qrl_file: Path) -> dict:
    query_list = {}

    for line in qrl_file.read_text(encoding="utf-8").split("\n"):
        if line.startswith(V_PREFIX):
            n = line.split(V_PREFIX)[-1]
            query_list[n] = {}
        elif line.startswith(M_PREFIX):
            r = line.split(M_PREFIX)[-1]
            query_list[n][r] = False
        elif line.startswith(Y_PREFIX):
            r = line.split(Y_PREFIX)[-1]
            query_list[n][r] = True

    return query_list


def dump_query_list_file(query_list: dict, qrl_file: Path) -> None:
    lines = []
    for name, result in query_list.items():
        lines.append(V_PREFIX + name)
        for r, y in result.items():
            lines.append((Y_PREFIX if y else M_PREFIX) + r)
        
        lines.append(SEPERATE)

    qrl_file.write_text("\n".join(lines), encoding="utf-8")


def generate_query_list(vgmdb_dir: Path, link_file: Path) -> dict:
    link = json.loads(link_file.read_text(encoding="utf-8")) if link_file.exists() else {}
    # 只允许扁平结构
    mdfs = [f for f in vgmdb_dir.glob("*.json") if str(f) not in link]
    query_list = {f.name: {} for f in mdfs}
    return query_list


def search_query_list(query_list: dict, vgmdb_dir: Path, mb_dir: Path) -> Generator[dict, None, None]:
    filter_mask = input("Please input filter mask [catalognumber, date, date_int, track_count] (default auto) : ")
    order_mask = input("Please input order mask [catalognumber, album, tracks_abstract] (default 111) : ").strip() or "111"

    # 直接指定 filter_mask 时才允许全表扫描
    allow_full_scan = bool(filter_mask)

    for name, result in query_list.items():

        # 跳过已搜索
        if result:
            continue
        
        a = load_album_model(Path(vgmdb_dir, name))
        
        filter_params = [a.catalognumber, a.date, sum(MusicBrainzDatabase._date_str_to_range(a.date))//2, len(a.tracks)]
        order_params = [a.catalognumber, a.album, MusicBrainzDatabase._abstract_tracks(a)]

        # 未输入 filter_mask ，则自动按优先级搜索
        # 自动搜索 不搜索日期 0100 搜不到 0010 很慢
        for mask in ([filter_mask] if filter_mask else ["1101", "1100", "1001", "1000"]):

            args1 = [x if int(b) else None for b, x in zip(mask, filter_params)]
            args2 = [x if int(b) else None for b, x in zip(order_mask, order_params)]

            mb_as = database.select_albums(None, *args1, *args2, allow_full_scan=allow_full_scan)

            # 未搜索出结果则继续
            if not mb_as:
                continue

            mb_mdfs = [mb_dir / (album_filename(mb_a)+".json") for mb_a in mb_as]
            [dump_album_model(mb_a, mb_mdf) for mb_a, mb_mdf in zip(mb_as, mb_mdfs)]
            query_list[name] = {os.path.basename(mb_mdf): False for mb_mdf in mb_mdfs}

            # 搜索出结果则退出
            break

        yield query_list


def apply_query_list(link: dict, query_list: dict, vgmdb_dir: Path, mb_dir: Path) -> dict:
    for name, result in query_list.items():
        if not result:
            continue

        mb_name = next((n for n, y in result.items() if y), None)
        if not mb_name:
            continue

        mdf = vgmdb_dir / name
        mb_mdf = mb_dir / mb_name

        link[str(mdf)] = str(mb_mdf)

    return link


def clean_mb_dir(link: dict, mb_dir: Path) -> None:
    # 清理 mb 目录
    files = mb_dir.rglob("*")
    vals = set(link.values())
    for f in files:
        if str(f) not in vals:
            f.unlink()


if __name__ == "__main__":

    # input 输入

    vgmdb_dir = input(f"Please input vgmdb directory: ").strip("'\"")
    mb_dir = input(f"Please input musicbrainz save directory: ").strip("'\"")
    tmp_dir = input(f"Please input temp directory ({TMP_PATH}): ").strip("'\"") or TMP_PATH

    if not vgmdb_dir or not mb_dir or not tmp_dir:
        sys.exit(0)

    vgmdb_dir, mb_dir, tmp_dir = Path(vgmdb_dir), Path(mb_dir), Path(tmp_dir)
    qrl_file = tmp_dir / "query_list.log"
    link_file = tmp_dir / "vgmdb2musicbrainz.json"

    database = MusicBrainzDatabase()

    # 循环交互

    while True:

        os.system("cls")
        print("Please input action number：")
        print("1. Generate query list file")
        print("2. Search query list file")
        print("3. Apply query list file")
        print("4. Clean musicbrainz save directory")
        action = int(input(""))

        if action == 1:
            query_list = generate_query_list(vgmdb_dir, link_file)
            dump_query_list_file(query_list, qrl_file)

        elif action == 2:
            query_list = load_query_list_file(qrl_file)
            for x in search_query_list(query_list, vgmdb_dir, mb_dir):
                dump_query_list_file(x, qrl_file)

        elif action == 3:
            link = json.loads(link_file.read_text(encoding="utf-8")) if link_file.exists() else {}
            query_list = load_query_list_file(qrl_file)

            link = apply_query_list(link, query_list, vgmdb_dir, mb_dir)
            link_file.write_text(json.dumps(link, ensure_ascii=False, indent=4), encoding="utf-8")

        elif action == 4:
            link = json.loads(link_file.read_text(encoding="utf-8")) if link_file.exists() else {}
            clean_mb_dir(link, mb_dir)




