import time
import shutil
from pathlib import Path

from tqdm import tqdm

from ongaku.core.logger import lprint
from ongaku.core.settings import  global_settings
from ongaku.workflow.utils import easy_linput


if global_settings.language == "zh":
    PLUGIN_NAME = "硬链接克隆"
    class MESSAGE:
        OLI4J5 = """
通过创建文件硬链接，镜像复制目标文件或文件夹。

原始路径：
    文件或文件夹，例如 D:\\1.txt ，例如 D:\\download。
目标父目录：
    必须与原始路径在同一磁盘，例如 D 盘。例如，输入 D:\\new\\ ，会在该父目录下创建同名对象。
    """
        SOPLP0 = "请输入原始文件或目录的路径："
        GFD8P9 = "请输入目标父目录："
        RE5LKM = "原始路径不存在。"
        IOP596 = "硬链接拷贝已完成。{:d} 个文件，{:d} 个文件夹，耗时 {:.2f} 秒。"
elif global_settings.language == "ja":
    pass
else:
    pass


################ 主函数 ################

def main():
    lprint(MESSAGE.OLI4J5)
    
    src_given = easy_linput(MESSAGE.SOPLP0, return_type=Path)
    dst_given = easy_linput(MESSAGE.GFD8P9, return_type=Path)

    if not src_given.exists():
        lprint(MESSAGE.RE5LKM)
        return
    
    dst = dst_given / src_given.name
    if dst.exists():
        dst = dst_given / f"{src_given.name} {int(time.time())}"

    st = time.time()

    # 仅单个文件
    if src_given.is_file():
        dst.hardlink_to(src_given)
        shutil.copystat(src_given, dst)
        lprint(MESSAGE.IOP596.format(1, 0, time.time()-st))
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

    lprint(MESSAGE.IOP596.format(file_count, dir_count, time.time()-st))
