import itertools
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tqdm import tqdm

from src.cli.common import easy_linput
from src.core.cache import with_cache
from src.core.i18n import MESSAGE
from src.core.kanban import Kanban
from src.core.logger import lprint
from src.core.settings import settings
from src.external import compress_png_file, rar_extract, rar_add, rar_list, rar_stats

OPERATION_NAME = MESSAGE.WF_20260128_092700


cached_rar_list = lambda dstrar: with_cache(rar_list, os.path.abspath(dstrar), related_file=os.path.abspath(dstrar))
cached_rar_stats = lambda dstrar: with_cache(rar_stats, os.path.abspath(dstrar), related_file=os.path.abspath(dstrar))


# 业务函数

def build_cache_rar() -> None:
    rar_files = list(Path(settings.resource_directory).rglob("*.rar"))
    if not rar_files:
        return

    pbar = tqdm(total=len(rar_files), desc=MESSAGE.WF_20260128_092703, miniters=1)
    executor = ThreadPoolExecutor()
    for f in rar_files:
        future = executor.submit(lambda f = f: [cached_rar_list(f), cached_rar_stats(f)])
        future.add_done_callback(lambda future: pbar.update(1))

    executor.shutdown()
    pbar.close()


def check_cover_size(kanban: Kanban) -> bool:
    lprint(f"{'-'*4} {MESSAGE.WF_20260128_092705} {'-'*4}")

    _list = []
    for ak in itertools.chain.from_iterable(tk.album_kanbans for tk in kanban.theme_kanbans):
        # flac 格式封面限制 16 MiB
        if not ak.cover_stat_result or ak.cover_stat_result.st_size < 16 * 1024 * 1024:
            continue

        _list.append(ak.cover_path)

    if not _list:
        lprint(MESSAGE.WF_20260128_092709)
        return True

    [lprint(os.path.join(parent, name)) for parent, name in _list]
    lprint(MESSAGE.WF_20260128_092706)
    if not easy_linput(MESSAGE.WF_20260128_092708, default="Y") == "Y":
        lprint(MESSAGE.WF_20260128_092711)
        return False

    pbar = tqdm(total=len(_list), miniters=1)

    for p in _list:
        pbar.update(1)

        if os.path.isdir(p[0]):
            compress_png_file(os.path.join(*p))
            continue

        with tempfile.TemporaryDirectory() as tempdir:
            rar_extract(*p, tempdir)
            cover = os.path.join(tempdir, p[1])
            compress_png_file(cover)
            rar_add(p[0], [cover])

    lprint(MESSAGE.WF_20260128_092710)
    lprint(MESSAGE.WF_20260128_092709)


def check_dirty_file(kanban: Kanban) -> bool:
    lprint(f"{'-'*4} {MESSAGE.WF_20260128_092712} {'-'*4}")

    aset = list(Path(settings.resource_directory).rglob("*"))
    aset.extend(os.path.join(p, n) for p in Path(settings.resource_directory).rglob("*.rar") for n in cached_rar_list(p))
    aset = set(map(str, aset))

    bset = []
    for tk in kanban.theme_kanbans:
        bset.append(tk.theme_resource_dir)
        for ak in tk.album_kanbans:
            bset.extend([ak.album_dir, ak.album_archive, *[os.path.join(*p) for p in [ak.cover_path, *ak.track_paths]]])
    bset = set(bset)

    min_len = len(min(bset, key=len))

    dirty = [p for p in (aset - bset) if len(p) >= min_len]
    if not dirty:
        lprint(MESSAGE.WF_20260128_092714)
        return

    [lprint(p) for p in dirty]
    lprint(MESSAGE.WF_20260128_092713)


# 主函数

def main() -> None:
    lprint(MESSAGE.WF_20260128_092700)
    kanban = Kanban(settings.metadata_directory, settings.resource_directory)

    build_cache_rar()

    check_cover_size(kanban)

    check_dirty_file(kanban)




