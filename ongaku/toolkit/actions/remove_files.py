import shutil
from pathlib import Path

from ongaku.logger import lprint
from ongaku.toolkit.toolkit_utils import easy_linput
from ongaku.toolkit.message import MESSAGE


def remove_files():

    lprint(MESSAGE.IXLSQ13W)
    
    given_path: Path = easy_linput(MESSAGE.K1ZZWV8C, return_type=Path)

    if not given_path.exists():
        lprint(MESSAGE.PK7LLJJU)
        return
    
    confirm: bool = easy_linput(MESSAGE.YO8JFLU3, default="N", return_type=str)  == "Y"

    if not confirm:
        return
    
    if given_path.is_symlink() or given_path.is_file():
        given_path.unlink()
    else:
        shutil.rmtree(given_path)
