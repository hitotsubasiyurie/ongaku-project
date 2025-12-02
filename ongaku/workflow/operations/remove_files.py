import time
import shutil
from pathlib import Path
from types import SimpleNamespace

from ongaku.core.logger import lprint
from ongaku.core.settings import  global_settings
from ongaku.workflow.common import easy_linput


if global_settings.language == "zh":
    OPERATION_NAME = "删除文件"
    class MESSAGE:
        OLI4J5 = """
删除路径文件或目录。不会挪至回收站，所以速度较快。
    """
        SOPLP0 = "请输入路径："
        GFD8P9 = "路径不存在。"
        RE5LKM = "是否确认删除（Y/N）（默认N）："
        IOP596 = "已删除。耗时 {:.2f} 秒。"
elif global_settings.language == "ja":
    pass
else:
    pass


################ 主函数 ################

def main():

    lprint(MESSAGE.OLI4J5)

    given_path = easy_linput(MESSAGE.SOPLP0, return_type=Path)

    if not given_path.exists():
        lprint(MESSAGE.GFD8P9)
        return
    
    if not easy_linput(MESSAGE.RE5LKM, default="N", return_type=str)  == "Y":
        return
    
    st = time.time()
    if given_path.is_symlink() or given_path.is_file():
        given_path.unlink()
    else:
        shutil.rmtree(given_path)
    
    lprint(MESSAGE.IOP596.format(time.time() - st))

