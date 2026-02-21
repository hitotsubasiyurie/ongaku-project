import shutil
from pathlib import Path

from src.cli.common import tracks_assignment, analyze_track
from src.core.basemodels import Album
from src.core.storage import track_stemnames, COVER_NAME
from src.ui.notifier import show_confirm_long_msg
from src.utils import convert_to_png


def put_away_cover_file(src: Path, dst_dir: Path) -> bool:
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / COVER_NAME
    dst.write_bytes(convert_to_png(src.read_bytes()))


def put_away_track_file(src: Path, dst_dir: Path, album: Album, trackidx: int) -> bool:
    dst_dir.mkdir(parents=True, exist_ok=True)
    ext = src.suffix.lower()
    dst = dst_dir / (track_stemnames(album)[trackidx]+ext)
    shutil.move(src, dst)
    return True


def put_away_track_files(src_files: list[Path], dst_dir: Path, album: Album) -> bool:
    dst_dir.mkdir(parents=True, exist_ok=True)

    src_tracks = list(map(analyze_track, src_files))
    row_ind, col_ind, aver_similarity, _ = tracks_assignment(src_tracks, album.tracks)

    dst_names = track_stemnames(album)
    _map: dict[Path, Path] = {src_files[r]: (dst_dir / (dst_names[c] + src_files[r].suffix.lower())) 
                                for r, c in zip(row_ind, col_ind)}

    text = f"""
Directory:\t\t{src_files[0].parent.name}
Album:\t\t{album.album}
Average Similarity:\t{aver_similarity:.02f}
"""
    text += "\n"*2 + "\n".join(f"    {k.name}\n->  {v.name}\n" for k, v in _map.items())
    accept = show_confirm_long_msg(text)

    if not accept:
        return False

    [shutil.move(src, dst) for src, dst in _map.items()]
    return True







