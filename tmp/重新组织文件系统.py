import sys
from pathlib import Path
import os

sys.path.append(r"E:\my\ongaku")
os.environ["ONGAKU_METADATA_PATH"] = r"D:\ongaku-metadata"
os.environ["ONGAKU_RESOURCE_PATH"] = r"D:\ongaku-resource"
os.environ["ONGAKU_TMP_PATH"] = r"D:\ongaku-tmp"

from src.ongaku_library.mdf_util import (load_album, get_track_states, track_filenames, _get_album_state, album_filename)


# metadata_dir = Path(input("请输入绝对 metadata 路径：").strip("'\""))
# resource_dir = Path(input("请输入绝对 resource 路径：").strip("'\""))

metadata_dir = Path(r"D:\ongaku-metadata")
resource_dir = Path(r"D:\ongaku-resource")

album_mdfs = list(metadata_dir.rglob("*.json"))
albums = list(map(load_album, album_mdfs))
_dname2path = {p.name: p for p in resource_dir.rglob("*") if p.is_dir()}
album_dirs = [_dname2path.get(f.stem, None) for f in album_mdfs]

for mdf, album, album_dir in zip(album_mdfs, albums, album_dirs):
    new_mdf = mdf.parent / (album_filename(album)+".json")
    if str(mdf) != str(new_mdf):
        mdf.rename(new_mdf)
        print("1")
    if not album_dir:
        continue
    new_album_dir = resource_dir / os.path.splitext(str(new_mdf.relative_to(metadata_dir)))[0]
    print(new_album_dir)
    if str(album_dir) != str(new_album_dir):
        new_album_dir.parent.mkdir(parents=True, exist_ok=True)
        album_dir.rename(new_album_dir)













