import itertools
from pathlib import Path
from datetime import datetime

from ongaku.core.logger import lprint, logger
from ongaku.core.settings import global_settings
from ongaku.core.kanban import load_albums_from_toml, dump_albums_to_toml
from ongaku.core.constants import AUDIO_EXTS
from ongaku.workflow.common import easy_linput
from ongaku.workflow.common import analyze_track, analyze_album


if global_settings.language == "zh":
    OPERATION_NAME = "从本地音频获取专辑元数据"
    class MESSAGE:
        OLI4J5 = """
保存路径：
    若是文件夹，将会在其下生成新的元数据文件。
    若是已有的元数据文件路径，将会追加它未包含的专辑元数据

音频资源父目录：
    
    """
        SOPLP0 = "请输入保存路径："
        DFT895 = "请输入音频资源父目录："
        RE5LKM = "解析完成。没有获得专辑元数据。"
        GFD8P9 = "解析完成。获得 {} 个专辑元数据，是否保存至 {} （Y/N）（默认Y）："
        IOP596 = "保存完成。"
elif global_settings.language == "ja":
    pass
else:
    pass


################ 主函数 ################

def main() -> None:
    lprint(MESSAGE.OLI4J5)

    input_path = easy_linput(MESSAGE.SOPLP0, return_type=Path)
    resource_directory = easy_linput(MESSAGE.DFT895, return_type=Path)

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
        lprint(MESSAGE.RE5LKM)
        return

    if not easy_linput(MESSAGE.GFD8P9.format(len(albums), metadata_file), default="Y", return_type=str)  == "Y":
        return

    exist_albums = load_albums_from_toml(metadata_file) if metadata_file.is_file() else []
    dump_albums_to_toml(exist_albums + albums, metadata_file)
    lprint(MESSAGE.IOP596)




















