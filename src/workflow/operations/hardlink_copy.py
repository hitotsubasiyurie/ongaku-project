import shutil
import time
from pathlib import Path

from tqdm import tqdm

from src.core.logger import lprint
from src.lang import MESSAGE
from src.workflow.common import easy_linput

OPERATION_NAME = MESSAGE.WF_20251204_195220


######## 主函数 ########

def main():
    lprint(MESSAGE.WF_20251204_195221)
    
    src_given = easy_linput(MESSAGE.WF_20251204_195222, return_type=Path)
    dst_given = easy_linput(MESSAGE.WF_20251204_195223, return_type=Path)

    if not src_given.exists():
        lprint(MESSAGE.WF_20251204_195224)
        return
    
    dst = dst_given / src_given.name
    if dst.exists():
        dst = dst_given / f"{src_given.name} {int(time.time())}"

    st = time.time()

    # 仅单个文件
    if src_given.is_file():
        dst.hardlink_to(src_given)
        shutil.copystat(src_given, dst)
        lprint(MESSAGE.WF_20251204_195225.format(1, 0, time.time()-st))
        return

    dst.mkdir(parents=True, exist_ok=True)

    src_files = list(src_given.rglob("*"))
    dst_files = [dst / s.relative_to(src_given) for s in src_files]

    file_count, dir_count = 0, 0
    for s, d in tqdm(zip(src_files, dst_files), total=len(src_files)):
        if s.is_dir():
            d.mkdir()
            dir_count += 1
        else:
            d.hardlink_to(s.resolve())
            shutil.copystat(s, d)
            file_count += 1

    # 倒序 复制目录元数据
    for s in tqdm(reversed(list(filter(Path.is_dir, src_files))), miniters=1):
        d = dst / s.relative_to(src_given)
        shutil.copystat(s, d)

    shutil.copystat(src_given, dst)

    lprint(MESSAGE.WF_20251204_195225.format(file_count, dir_count, time.time()-st))
