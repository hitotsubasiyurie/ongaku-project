import shutil
import time
from pathlib import Path

from src.core.logger import lprint
from src.lang import MESSAGE
from src.workflow.common import easy_linput

OPERATION_NAME = MESSAGE.WF_20251204_194320

######## 主函数 ########

def main():

    lprint(MESSAGE.WF_20251204_194321)

    given_path = easy_linput(MESSAGE.WF_20251204_194322, return_type=Path)

    if not given_path.exists():
        lprint(MESSAGE.WF_20251204_194323)
        return
    
    if not easy_linput(MESSAGE.WF_20251204_194324, default="N", return_type=str)  == "Y":
        return
    
    st = time.time()
    if given_path.is_symlink() or given_path.is_file():
        given_path.unlink()
    else:
        shutil.rmtree(given_path)
    
    lprint(MESSAGE.WF_20251204_194325.format(time.time() - st))

