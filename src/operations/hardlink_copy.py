import filecmp
import shutil
import time
from datetime import datetime
from pathlib import Path

from tqdm import tqdm

from src.core.i18n import g_message
from src.core.console import cinput, cprint, easy_linput

OPERATION_NAME = g_message.WF_20251204_195220

# 业务函数

def get_dirty_files(src: Path, dst: Path) -> list[Path]:
    """
    获取脏文件。
    在源中没有的文件，与源不同的文件，被认为是脏文件。

    :param src: 文件或目录
    :param dst: 文件或目录
    """
    if src.is_file():
        return [dst] if not filecmp.cmp(src, dst) else []
    
    d_paths: list[Path] = list(dst.rglob("*"))
    dirty = []

    for d in d_paths:
        s = src / d.relative_to(dst)
        # 源不存在，或者文件类型不同时
        if not s.exists() or s.is_file() != d.is_file():
            dirty.append(d)
            continue
        # 文件不同时
        if d.is_file() and not filecmp.cmp(s, d):
            dirty.append(d)

    return dirty


def _hardlink_copy(src: Path, dst: Path) -> tuple[int, int]:
    """
    硬链接克隆。

    :return: 文件数，目录数
    """
    if src.is_file():
        s_paths = [src]
        d_paths = [dst]
    else:
        # 广度优先顺序
        s_paths = [src] + list(src.rglob("*"))
        d_paths = [dst / s.relative_to(src) for s in s_paths]

    sd_dirs = []
    file_count, dir_count = 0, 0
    for s, d in tqdm(zip(s_paths, d_paths), total=len(s_paths)):
        if s.is_dir():
            d.mkdir(exist_ok=True)
            sd_dirs.append((s, d))
            dir_count += 1
            continue

        if not d.is_file():
            d.hardlink_to(s.resolve())
            shutil.copystat(s, d)
        file_count += 1

    # 倒序 复制目录元数据
    for s, d in tqdm(reversed(sd_dirs), total=len(sd_dirs), miniters=1):
        shutil.copystat(s, d)

    return file_count, dir_count

# 主函数

def hardlink_copy():
    cprint(g_message.WF_20251204_195221)

    src = easy_linput(g_message.WF_20251204_195222, return_type=Path)
    dst_parent = easy_linput(g_message.WF_20251204_195223, return_type=Path)

    if not src.exists():
        cprint(g_message.WF_20251204_195224)
        return

    dst = dst_parent / src.name

    # 若目标存在，文件类型不同时或是用户选择时，使用新位置克隆
    if dst.exists():
        if src.is_file() != dst.is_file() or not easy_linput(g_message.WF_20251204_195226, default="Y", return_type=str) == "Y":
            dst = dst_parent / f"{src.name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # 若目标存在，删除差异文件
    if dst.exists():
        dirty = list(reversed(get_dirty_files(src, dst)))
        if dirty:
            [cprint(p) for p in dirty]
            if not easy_linput(g_message.WF_20251204_195227, default="Y", return_type=str) == "Y":
                return
            [p.unlink() if p.is_file() else p.rmdir() for p in dirty]

    st = time.time()

    c1, c2 = _hardlink_copy(src, dst)

    cprint(g_message.WF_20251204_195225.format(c1, c2, time.time()-st))



