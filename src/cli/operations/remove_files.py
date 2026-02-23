import shutil
import time
from pathlib import Path

from src.cli.common import easy_linput
from src.core.i18n import g_message
from src.core.logger import lprint

OPERATION_NAME = g_message.WF_20251204_194320

# 主函数

def remove_files():

    lprint(g_message.WF_20251204_194321)

    given_path = easy_linput(g_message.WF_20251204_194322, return_type=Path)

    if not given_path.exists():
        lprint(g_message.WF_20251204_194323)
        return
    
    if not easy_linput(g_message.WF_20251204_194324, default="N", return_type=str)  == "Y":
        return
    
    st = time.time()
    if given_path.is_symlink() or given_path.is_file():
        given_path.unlink()
    else:
        shutil.rmtree(given_path)
    
    lprint(g_message.WF_20251204_194325.format(time.time() - st))



