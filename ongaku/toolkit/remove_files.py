import time
import shutil
from pathlib import Path
from types import SimpleNamespace

from ongaku.core.logger import lprint
from ongaku.core.settings import  global_settings
from ongaku.toolkit.utils import easy_linput


if global_settings.language == "zh":
    PLUGIN_NAME = "删除文件"
elif global_settings.language == "ja":
    pass
else:
    PLUGIN_NAME = "Remove file"


MESSAGE = SimpleNamespace()


if global_settings.language == "zh":
    MESSAGE.C3X = \
"""
删除路径文件或目录。不会挪至回收站，所以速度较快。
"""
    MESSAGE.OG9 = "请输入路径："
    MESSAGE.AAR = "路径不存在。"
    MESSAGE.G9R = "是否确认删除（Y/N）（默认N）："
    MESSAGE.B21 = "已删除。耗时 {:.2f} 秒。"


def main():

    lprint(MESSAGE.C3X)

    given_path = easy_linput(MESSAGE.OG9, return_type=Path)

    if not given_path.exists():
        lprint(MESSAGE.AAR)
        return
    
    confirm = easy_linput(MESSAGE.G9R, default="N", return_type=str)  == "Y"

    if not confirm:
        return
    
    st = time.time()
    if given_path.is_symlink() or given_path.is_file():
        given_path.unlink()
    else:
        shutil.rmtree(given_path)
    
    lprint(MESSAGE.B21.format(time.time() - st))

