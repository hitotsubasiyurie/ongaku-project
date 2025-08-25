import sys
import json
import os
from pathlib import Path

import orjson
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.logger import logger, _ongaku_logger
from src.metadata_source.musicbrainz_api import MusicBrainzAPI
from src.metadata_source.musicbrainz_database import MusicBrainzDatabase
from src.common.basemodels import Album
from src.repository.ongaku_repository import dump_albums_to_toml, load_albums_from_toml


SEPERATE = f"\n{'-'*16} seperate {'-'*16}\n"

SRC_ALBUM = "SRC_ALBUM: "
GOT_ALBUM = "GOT_ALBUM: "
MATCH_ALBUM = "MATCH_ALBUM: "


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




def generate_merge_log(src_albums: list[Album], merge_log_file: Path) -> None:
    content = merge_log_file.read_text("utf-8") if merge_log_file.exists() else ""

    filter_mask = input("Please input filter mask [catalognumber, date, date_int, track_count]\n" \
                        "(recommend 1101 -> 1100 -> 1001 -> 1000): ")
    order_mask = input("Please input similarity order mask [catalognumber, album, tracks_abstract] (default 111) : ").strip() or "111"

    pbar = tqdm(total=len(src_albums), mininterval=0)
    for src_album in src_albums:

        unique_str = album_to_unique_str(src_album)

        # 跳过 已搜索
        if unique_str in content:
            pbar.update()
            continue

        filter_params = [src_album.catalognumber, src_album.date, 
                         sum(MusicBrainzDatabase._date_str_to_range(src_album.date))//2, len(src_album.tracks)]
        order_params = [src_album.catalognumber, src_album.album, abstract_tracks_info(src_album)]

        args1 = [x if int(b) else None for b, x in zip(filter_mask, filter_params)]
        args2 = [x if int(b) else None for b, x in zip(order_mask, order_params)]

        # 允许 全表扫描
        got_albums = database.select_albums(None, None, *args1, *args2, allow_full_scan=True)

        lines = []
        lines.append(SRC_ALBUM + unique_str)
        lines.append("")

        # TODO:  apply 时 怎么根据 unique_str 获取 mb album
        [lines.append(GOT_ALBUM + album_to_unique_str(a)) for a in got_albums]
        
        pbar.update()
        content += SEPERATE.join(lines)
    
    merge_log_file.write_text(content, encoding="utf-8")


if __name__ == "__main__":

    # input 输入
    
    metadata_dir = input(f"Please input metadata directory: ").strip("'\"")
    theme = input(f"Please input theme: ").strip() 

    if not metadata_dir or not theme:
        sys.exit(0)

    metadata_dir = Path(metadata_dir)

    theme_pending_file = Path(metadata_dir, theme + ".pending" + ".toml")
    merge_log_file = Path(metadata_dir, "merge.log")

    # 日志输出至文件
    if not _ongaku_logger.outfile:
        _ongaku_logger.set_outfile(metadata_dir / )


    database = MusicBrainzDatabase()

    src_albums = load_albums_from_toml(theme_pending_file)
    unique_str_to_album = {album_to_unique_str(a): a for a  in src_albums}

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
            generate_merge_log(src_albums, merge_log_file)





