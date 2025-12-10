import itertools
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path

from mutagen.flac import FLAC
from mutagen.id3 import ID3, APIC
from mutagen.mp3 import MP3

from src.core.basemodels import Album, Track
from src.core.kanban import KanBan, track_filenames
from src.core.logger import lprint, logger
from src.core.settings import global_settings
from src.external import show_audio_stream_info, compress_image
from src.lang import MESSAGE
from src.utils import write_audio_tags, read_audio_tags
from src.workflow.common import easy_linput

OPERATION_NAME = MESSAGE.WF_20251204_194420


######## 工具函数 ########

def fuzzy_compare_audios(audio1: str | Path, audio2: str | Path) -> True:
    """
    比较 audio1 与 audio2 音频流信息是否一致。
    """
    result = json.dumps(show_audio_stream_info(str(audio1))) == json.dumps(show_audio_stream_info(str(audio2)))
    logger.info(f"Fuzzy compare audios: {result} {audio1} {audio2}")
    return result


def fuzzy_compare_cover(audio: str | Path, cover: str | Path) -> bool:
    """
    比较 audio 封面与 cover 数据大小是否一致。
    """
    audio, cover = Path(audio), Path(cover)

    if audio.suffix.lower() == ".flac":
        flac = FLAC(audio)
        # 无封面
        if not flac.pictures:
            logger.info(f"Fuzzy compare cover: False, no cover.")
            return False
        audio_cover_data = flac.pictures[0].data

    elif audio.suffix.lower() == ".mp3":
        mp3 = MP3(audio, ID3=ID3)
        # 无封面
        apic_tag = next((t for t in mp3.tags.values() if isinstance(t, APIC)), None)
        if not apic_tag:
            logger.info(f"Fuzzy compare cover: False, no cover.")
            return False
        audio_cover_data = apic_tag.data

    audio_cover_size, cover_size = len(audio_cover_data), cover.stat().st_size
    result = audio_cover_size == cover_size
    logger.info(f"Fuzzy compare cover: {result} {(audio_cover_size, cover_size)} {audio} {cover}")
    return result


def write_metadata(dst_file: str | Path, cover: str, album: Album, track: Track) -> None:
    """
    向 dst_file 写入元数据。
    """
    # flac 格式封面限制 16 MiB
    if Path(cover).stat().st_size >= 16 * 1024 * 1024:
        lprint(MESSAGE.WF_20251204_194431.format(cover))
        compress_image(cover)

    write_audio_tags(str(dst_file), cover, 
                     album.catalognumber, album.date, album.album, 
                     str(track.tracknumber), track.title, track.artist)


_NON_CONFLICTING_SUFFIX = re.compile(r" \((\d+)\)$")

def get_non_conflicting_path(anypath: Path) -> Path:
    """
    获取不冲突的路径，如 D:\\1.txt -> D:\\1 (1).txt 。
    """
    if not anypath.exists():
        return anypath
    match = _NON_CONFLICTING_SUFFIX.search(anypath.stem)
    num = int(match.group(1)) + 1 if match else 1
    base_name = _NON_CONFLICTING_SUFFIX.sub("", anypath.stem)
    new_path = anypath.with_name(f"{base_name} ({num}){anypath.suffix}")
    return get_non_conflicting_path(new_path)


def remove_non_conflicting_suffix(anypath: Path) -> Path:
    """
    移除不冲突的后缀，如 D:\\1 (1).txt -> D:\\1.txt 。
    """
    base_name = _NON_CONFLICTING_SUFFIX.sub("", anypath.stem)
    return anypath.with_name(f"{base_name}{anypath.suffix}")


######## 主函数 ########

def main() -> None:
    lprint(MESSAGE.WF_20251204_194421)

    export_dir = easy_linput(MESSAGE.WF_20251204_194422, return_type=Path)
    
    kanban = KanBan(global_settings.metadata_directory, global_settings.resource_directory)

    total = sum(1 for tk in kanban.theme_kanbans for ak in tk.album_kanbans for t in ak.album.tracks if t.mark == "1")
    current = 0

    delete_files = []

    for theme_kanban in kanban.theme_kanbans:
        theme_export_dir = export_dir / theme_kanban.theme_name
        theme_export_dir.mkdir(parents=True, exist_ok=True)

        existing_files: dict[str, list[Path]] = defaultdict(list)
        [existing_files[remove_non_conflicting_suffix(f).name].append(f) for f in theme_export_dir.iterdir()]

        for album_kanban in theme_kanban.album_kanbans:
            album = album_kanban.album

            for idx, track in enumerate(album.tracks):

                # 跳过非 favourite
                if track.mark != "1":
                    continue

                current += 1

                # 资源不存在
                if not album_kanban.track_files[idx]:
                    src_file = Path(album_kanban.album_dir, track_filenames(album)[idx])
                    if not easy_linput(MESSAGE.WF_20251204_194427.format(current, total, src_file), default="N", return_type=str)  == "Y":
                        return
                
                # 封面不存在
                if not album_kanban.cover:
                    if not easy_linput(MESSAGE.WF_20251204_194428.format(current, total, album_kanban.album_dir), default="N", return_type=str)  == "Y":
                        return

                src_file = Path(album_kanban.track_files[idx])

                # 去掉轨道号前缀 "2. 風への誓い.mp3" -> "風への誓い.mp3"
                dst_name = src_file.name.split(" ", maxsplit=1)[1]

                # 寻找已存在的导出文件 模糊比较音频
                dst_file = None
                if dst_name in existing_files:
                    dst_i = next((i for i, f in enumerate(existing_files[dst_name]) if fuzzy_compare_audios(src_file, f)), None)
                    if dst_i is not None:
                        dst_file = existing_files[dst_name].pop(dst_i)
                        logger.info(f"Found exported resource: {dst_file}")

                # 找不到 导出文件
                if dst_file is None:
                    dst_file = get_non_conflicting_path(Path(theme_export_dir, dst_name))

                # 资源已存在
                if dst_file.exists():
                    lprint(MESSAGE.WF_20251204_194424.format(current, total, src_file, dst_file))
                    # 重新计算 非冲突后缀
                    if _NON_CONFLICTING_SUFFIX.search(dst_file.stem):
                        new_file = get_non_conflicting_path(remove_non_conflicting_suffix(dst_file))
                        if dst_file != new_file:
                            dst_file.rename(new_file)
                            lprint(MESSAGE.WF_20251204_194426.format(current, total, dst_file, new_file))
                            dst_file = new_file
                    # 元数据不一致 封面不一致 重新写入 元数据
                    src_tags = (album.catalognumber, album.date, album.album, str(track.tracknumber), track.title, track.artist)
                    dst_tags = tuple(read_audio_tags(dst_file, standard=True).values())
                    if any((v1 and v1 != v2) for v1, v2 in zip(src_tags, dst_tags)) or not fuzzy_compare_cover(dst_file, album_kanban.cover):
                        logger.info(f"Metadata are not the same. {src_tags} {dst_tags}")
                        write_metadata(dst_file, album_kanban.cover, album, track)
                        lprint(MESSAGE.WF_20251204_194425.format(current, total, dst_file))
                # 资源不存在 导出资源
                else:
                    shutil.copy2(src_file, dst_file)
                    write_metadata(dst_file, album_kanban.cover, album, track)
                    lprint(MESSAGE.WF_20251204_194423.format(current, total, src_file, dst_file))
                    continue

        # 剩余存在的未处理的文件
        delete_files.extend(itertools.chain.from_iterable(list(existing_files.values())))
    
    # 删除多余导出文件
    for f in delete_files:
        if easy_linput(MESSAGE.WF_20251204_194429.format(f), default="Y", return_type=str)  == "Y":
            f.unlink()

    lprint(MESSAGE.WF_20251204_194432)


