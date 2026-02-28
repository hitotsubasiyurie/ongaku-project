import shutil
import time
from pathlib import Path

from src.core.i18n import g_message
from src.core.console import cinput, cprint, easy_cinput

OPERATION_NAME = g_message.WF_20251204_194320

# 主函数

def remove_files():

    cprint(g_message.WF_20251204_194321)

    given_path = easy_cinput(g_message.WF_20251204_194322, return_type=Path)

    if not given_path.exists():
        cprint(g_message.WF_20251204_194323)
        return
    
    if not easy_cinput(g_message.WF_20251204_194324, default="N", return_type=str)  == "Y":
        return
    
    st = time.time()
    if given_path.is_symlink() or given_path.is_file():
        given_path.unlink()
    else:
        shutil.rmtree(given_path)
    
    cprint(g_message.WF_20251204_194325.format(time.time() - st))



