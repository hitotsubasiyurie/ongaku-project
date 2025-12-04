import itertools
from pathlib import Path
from datetime import datetime

from ongaku.core.logger import lprint, logger
from ongaku.core.kanban import load_albums_from_toml, dump_albums_to_toml
from ongaku.lang import MESSAGE
from ongaku.core.constants import AUDIO_EXTS
from ongaku.workflow.common import easy_linput
from ongaku.workflow.common import analyze_album


OPERATION_NAME = MESSAGE.WF_20251204_194620


######## 主函数 ########

def main() -> None:
    lprint(MESSAGE.WF_20251204_194621)

    input_path = easy_linput(MESSAGE.WF_20251204_194622, return_type=Path)
    resource_directory = easy_linput(MESSAGE.WF_20251204_194623, return_type=Path)

    # 创建目录
    if input_path.is_file():
        input_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_file = input_path
    else:
        input_path.mkdir(parents=True, exist_ok=True)
        metadata_file = input_path / f"Fetch-{datetime.now().strftime("%Y%m%d_%H%M%S")}.toml"


    # 扁平、存在音频 的目录 认为是专辑目录
    album_dirs = [d for d in resource_directory.rglob("*") 
                if d.is_dir() 
                and all(f.is_file() for f in d.glob("*"))
                and list(itertools.chain.from_iterable(d.glob(f"*{ext}") for ext in AUDIO_EXTS))]

    albums = list(map(analyze_album, album_dirs))

    if not albums:
        lprint(MESSAGE.WF_20251204_194624)
        return

    if not easy_linput(MESSAGE.WF_20251204_194625.format(len(albums), metadata_file), default="Y", return_type=str)  == "Y":
        return

    exist_albums = load_albums_from_toml(metadata_file) if metadata_file.is_file() else []
    dump_albums_to_toml(exist_albums + albums, metadata_file)
    lprint(MESSAGE.WF_20251204_194626)




















