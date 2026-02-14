import itertools
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tqdm import tqdm

from src.cli.common import easy_linput
from src.core.i18n import MESSAGE
from src.core.kanban import track_stemnames, _cached_rar_list, _cached_rar_stats
from src.core.logger import lprint
from src.core.settings import settings
from src.external import compress_image, rar_extract, rar_add

OPERATION_NAME = MESSAGE.WF_20260128_092700


# 业务函数

def scan_archive_directory() -> None:
    rar_files = list(map(os.path.abspath, Path(settings.archive_directory).rglob("*.rar")))
    if not rar_files:
        return

    lprint(MESSAGE.WF_20260128_092703)

    pbar = tqdm(total=len(rar_files), miniters=1)
    executor = ThreadPoolExecutor()
    for f in rar_files:
        future = executor.submit(lambda f = f: _cached_rar_stats(f, _cached_rar_list(f)))
        future.add_done_callback(lambda future: pbar.update(1))

    executor.shutdown()
    pbar.close()


def check_favourites(kanban: Kanban) -> None:
    lprint(MESSAGE.WF_20260128_092704)

    missing_favs, missing_covers = [], []

    for ak in itertools.chain.from_iterable(tk.album_kanbans for tk in kanban.theme_kanbans):
        idxs = [i for i, t in enumerate(ak.album.tracks) if t.mark == "1"]
        if not idxs:
            continue
        parent = ak.album_dir or ak.album_archive
        if not ak.cover_filename:
            missing_covers.append(parent)
        missing_idxs = [i for i in idxs if not ak.track_filenames[i]]
        stemnames = track_stemnames(ak.album)
        missing_favs.extend(os.path.join(parent, stemnames[i]) for i in missing_idxs)

    if missing_favs or missing_covers:
        missing_favs and [lprint(f) for f in missing_favs] and lprint(MESSAGE.WF_20251204_194427)
        missing_covers and [lprint(f) for f in missing_covers] and lprint(MESSAGE.WF_20251204_194428)
    else:
        lprint(MESSAGE.WF_20260128_092707)


def check_cover_size(kanban: Kanban) -> bool:
    lprint(MESSAGE.WF_20260128_092705)

    _list = []
    for ak in itertools.chain.from_iterable(tk.album_kanbans for tk in kanban.theme_kanbans):
        # flac 格式封面限制 16 MiB
        if not ak.cover_filename or ak.cover_stat_result.st_size < 16 * 1024 * 1024:
            continue

        parent = ak.album_dir or ak.album_archive
        _list.append((parent, ak.cover_filename))
    
    if not _list:
        lprint(MESSAGE.WF_20260128_092709)
        return
    
    [lprint(os.path.join(parent, name)) for parent, name in _list]
    lprint(MESSAGE.WF_20260128_092706)
    if not easy_linput(MESSAGE.WF_20260128_092708, default="Y") == "Y":
        return False

    pbar = tqdm(total=len(_list), miniters=1)

    for parent, name in _list:
        pbar.update(1)

        if os.path.isdir(parent):
            compress_image(os.path.join(parent, name))
            continue

        with tempfile.TemporaryDirectory() as tempdir:
            rar_extract(parent, name, tempdir)
            cover = os.path.join(tempdir, name)
            compress_image(cover)
            rar_add(parent, [cover])
    
    lprint(MESSAGE.WF_20260128_092710)


# 主函数

def main() -> None:
    lprint(MESSAGE.WF_20260128_092700)

    scan_archive_directory()

    kanban = Kanban(settings.metadata_directory, settings.resource_directory, settings.archive_directory)

    check_favourites(kanban)

    if not check_cover_size(kanban):
        return
    


















