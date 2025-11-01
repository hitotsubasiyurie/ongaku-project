import time
import shutil
from pathlib import Path
from types import SimpleNamespace

from tqdm import tqdm

from ongaku.core.logger import lprint
from ongaku.core.settings import  global_settings
from ongaku.toolkit.toolkit_utils import easy_linput


if global_settings.language == "zh":
    PLUGIN_NAME = "硬链接克隆"
elif global_settings.language == "ja":
    PLUGIN_NAME = "ハードリンククローン"
else:
    PLUGIN_NAME = "Hardlink Clone"


MESSAGE = SimpleNamespace()


if global_settings.language == "zh":
    MESSAGE.C3X = \
"""
通过创建文件硬链接，镜像复制目标文件或文件夹。

原始路径：
    文件或文件夹，例如 D:\\1.txt ，例如 D:\\download。
目标父目录：
    必须与原始路径在同一磁盘，例如 D 盘。例如，输入 D:\\new\\ ，会在该父目录下创建同名对象。
"""
    MESSAGE.OG9 = "请输入原始文件或目录的路径："
    MESSAGE.K98 = "请输入目标父目录："
    MESSAGE.AAR = "原始路径不存在。"
    MESSAGE.B21 = "硬链接拷贝已完成。{:d} 个文件，{:d} 个文件夹，耗时 {:.2f} 秒。"

elif global_settings.language == "ja":
    MESSAGE.C3X = \
"""
ファイルのハードリンクを作成して、元のファイルまたはフォルダーをミラーコピーします。

元のパス：
    ファイルまたはフォルダー（例：D:\\1.txt、D:\\download）
ターゲット親ディレクトリ：
    元のパスと同じディスク上である必要があります（例：Dドライブ）。
    たとえば D:\\new\\ を入力すると、その親ディレクトリの下に同名のオブジェクトが作成されます。
"""
    MESSAGE.OG9 = "元のファイルまたはディレクトリのパスを入力してください："
    MESSAGE.K98 = "ターゲットの親ディレクトリを入力してください："
    MESSAGE.AAR = "元のパスが存在しません。"
    MESSAGE.B21 = "ハードリンクコピーが完了しました。ファイル {:d} 個、フォルダー {:d} 個、所要時間 {:.2f} 秒。"

else:
    MESSAGE.C3X = \
"""
Mirror-copy a file or folder by creating hard links.

Source path:
    A file or folder, e.g. D:\\1.txt or D:\\download
Target parent directory:
    Must be on the same disk as the source path (e.g. drive D:).
    For example, entering D:\\new\\ will create an object with the same name under that directory.
"""
    MESSAGE.OG9 = "Please enter the path of the original file or directory:"
    MESSAGE.K98 = "Please enter the target parent directory:"
    MESSAGE.AAR = "The source path does not exist."
    MESSAGE.B21 = "Hardlink copy completed. {:d} files, {:d} folders, took {:.2f} seconds."


def main():
    lprint(MESSAGE.C3X)
    
    src_given = easy_linput(MESSAGE.OG9, return_type=Path)
    dst_given = easy_linput(MESSAGE.K98, return_type=Path)

    if not src_given.exists():
        lprint(MESSAGE.AAR)
        return
    
    dst = dst_given / src_given.name
    if dst.exists():
        dst = dst_given / (src_given.name + str(int(time.time())))

    st = time.time()

    # 仅单个文件
    if src_given.is_file():
        dst.hardlink_to(src_given)
        shutil.copystat(src_given, dst)
        lprint(MESSAGE.B21.format(1, 0, time.time()-st))
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
    for s in tqdm(reversed(list(filter(Path.is_dir, src_files)))):
        d = dst / s.relative_to(src_given)
        shutil.copystat(s, d)

    shutil.copystat(src_given, dst)

    lprint(MESSAGE.B21.format(file_count, dir_count, time.time()-st))
