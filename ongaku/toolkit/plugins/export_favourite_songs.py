import re
import json
import shutil
import itertools
from collections import defaultdict
from pathlib import Path

from ongaku.core.logger import lprint, logger
from ongaku.core.settings import global_settings
from ongaku.core.kanban import KanBan, track_filenames
from ongaku.core.basemodels import Album, Track
from ongaku.toolkit.toolkit_utils import easy_linput
from ongaku.utils.utils import write_audio_tags, read_audio_tags
from ongaku.external import show_audio_stream_info, compress_image


if global_settings.language == "zh":
    PLUGIN_NAME = "导出喜欢的歌曲"
    class MESSAGE:
        OLI = """
导出目录路径：
    例如 D:\\ongaku-export
    """
        SOP = "请输入导出目录路径："
        GFD = "【{}/{}】已导出：{} -> {}"
        RE5 = "【{}/{}】已存在：{} -> {}"
        DD8 = "【{}/{}】已修改标签：{}"
        SS2 = "【{}/{}】资源不存在！{}"
        PO0 = "是否删除导出目录中的多余文件：{} （Y/N）（默认Y）："
        LKO = "压缩封面图像：{}"
elif global_settings.language == "ja":
    pass
else:
    pass


def fuzzy_compare_audios(audio1: str | Path, audio2: str | Path) -> True:
    result = json.dumps(show_audio_stream_info(str(audio1))) == json.dumps(show_audio_stream_info(str(audio2)))
    logger.info(f"Fuzzy compare audios: {result} {audio1} {audio2}")
    return result


def write_tags(dst_file: str | Path, cover: str, album: Album, track: Track) -> None:
    # flac 格式封面限制 16 MiB
    if Path(cover).stat().st_size >= 16 * 1024 * 1024:
        lprint(MESSAGE.LKO.format(cover))
        compress_image(cover)

    write_audio_tags(str(dst_file), cover, 
                     album.catalognumber, album.date, album.album, 
                     str(track.tracknumber), track.title, track.artist)


_UNIQUE_SUFFIX = re.compile(r" \((\d+)\)$")

def make_unique_path(anypath: Path) -> Path:
    if not anypath.exists():
        return anypath
    match = _UNIQUE_SUFFIX.search(anypath.stem)
    num = int(match.group(1)) + 1 if match else 1
    base_name = _UNIQUE_SUFFIX.sub("", anypath.stem)
    new_path = anypath.with_name(f"{base_name} ({num}){anypath.suffix}")
    return make_unique_path(new_path)


def remove_unique_suffix(anypath: Path) -> Path:
    base_name = _UNIQUE_SUFFIX.sub("", anypath.stem)
    return anypath.with_name(f"{base_name}{anypath.suffix}")


def main() -> None:
    lprint(MESSAGE.OLI)

    export_dir = easy_linput(MESSAGE.SOP, return_type=Path)
    
    kanban = KanBan(global_settings.metadata_directory, global_settings.resource_directory)

    total = sum(1 for tk in kanban.theme_kanbans for ak in tk.album_kanbans for t in ak.album.tracks if t.mark == "1")
    current = 0

    delete_files = []

    for theme_kanban in kanban.theme_kanbans:
        theme_export_dir = export_dir / theme_kanban.theme_name
        theme_export_dir.mkdir(parents=True, exist_ok=True)

        existing_files: dict[str, list[Path]] = defaultdict(list)
        [existing_files[remove_unique_suffix(f).name].append(f) for f in theme_export_dir.iterdir()]

        for album_kanban in theme_kanban.album_kanbans:
            album = album_kanban.album

            for idx, track in enumerate(album.tracks):

                # 无资源时 或着 非 favourite 时 跳过
                if track.mark != "1":
                    continue

                current += 1

                # 喜欢的资源不存在
                if not album_kanban.track_files[idx]:
                    lprint(MESSAGE.SS2.format(current, total, Path(album_kanban.album_dir, track_filenames(album)[idx])))
                    continue
                
                src_file = Path(album_kanban.track_files[idx])

                dst_name = src_file.name.split(" ", maxsplit=1)[1]
                # 寻找已存在的导出目的
                dst_file = None
                if dst_name in existing_files:
                    dst_i = next((i for i, f in enumerate(existing_files[dst_name]) if fuzzy_compare_audios(src_file, f)), None)
                    if dst_i is not None:
                        dst_file = existing_files[dst_name].pop(dst_i)
                        logger.info(f"Found exported resource: {dst_file}")

                if dst_file is None:
                    dst_file = make_unique_path(Path(theme_export_dir, dst_name))

                if dst_file.exists():
                    # 资源已存在
                    lprint(MESSAGE.RE5.format(current, total, src_file, dst_file))
                    # 元数据不一致 重写标签
                    src_tags = (album.catalognumber, album.date, album.album, str(track.tracknumber), track.title, track.artist)
                    dst_tags = tuple(read_audio_tags(dst_file, standard=True).values())
                    if any((v1 and v1 != v2) for v1, v2 in zip(src_tags, dst_tags)):
                        logger.info(f"Tags are not the same. {src_tags} {dst_tags}")
                        write_tags(dst_file, album_kanban.cover, album, track)
                        lprint(MESSAGE.DD8.format(current, total, dst_file))
                else:
                    # 导出资源
                    shutil.copy2(src_file, dst_file)
                    write_tags(dst_file, album_kanban.cover, album, track)
                    lprint(MESSAGE.GFD.format(current, total, src_file, dst_file))
                    continue

        delete_files.extend(itertools.chain.from_iterable(list(existing_files.values())))
    
    # 删除多余导出文件
    for f in delete_files:
        if easy_linput(MESSAGE.PO0.format(f), default="Y", return_type=str)  == "Y":
            f.unlink()



