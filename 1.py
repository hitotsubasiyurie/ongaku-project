import shutil
from pathlib import Path




srcdir = Path(r"D:\ongaku-archive")
dstdir = Path(r"D:\分批次克隆")

srcfiles = list(filter(Path.is_file, srcdir.rglob("*")))

MAX_SIZE = 120 * 1024 * 1024 * 1024

batch = 1
batch_size = 0

for srcfile in srcfiles:

    batch_dir = Path(dstdir, str(batch))
    dstfile = Path(batch_dir, srcfile.relative_to(srcdir))

    dstfile.parent.mkdir(parents=True, exist_ok=True)
    dstfile.hardlink_to(srcfile)
    shutil.copystat(srcfile, dstfile)

    batch_size += srcfile.stat().st_size

    if batch_size > MAX_SIZE:
        batch += 1
        batch_size = 0











