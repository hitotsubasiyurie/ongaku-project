import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

from ongaku.core.logger import lprint, logger
from ongaku.core.settings import global_settings
from ongaku.core.kanban import KanBan
from ongaku.core.basemodels import Album, Track
from ongaku.toolkit.toolkit_utils import easy_linput
from ongaku.utils.utils import write_audio_tags, read_audio_tags, legalize_filename, \
    compress_img_by_pngquant


if global_settings.language == "zh":
    PLUGIN_NAME = "导出喜欢的歌曲"
elif global_settings.language == "ja":
    pass
else:
    pass


MESSAGE = SimpleNamespace()


if global_settings.language == "zh":
    MESSAGE.SOP = "请输入导出目录路径："
    MESSAGE.GFD = "【{}/{}】{} -> {}"
    MESSAGE.LKO = "正在压缩封面图像：{}"
    MESSAGE.RE5 = "【{}/{}】已存在。 {}"
    MESSAGE.BN8 = "{}\n -> {}\n是否覆盖（Y/N）（默认N）："
elif global_settings.language == "ja":
    pass
else:
    pass


def is_audios_same(file1: str, file2: str) -> bool:
    """
    检查音频内容是否一致。
    """
    def get_pcm_bytes(file: str) -> bytes:
        ffmpeg_path = r".\dependency\ffmpeg.exe"
        cmd = [ffmpeg_path, "-i", file, "-f", "s16le", "-"]
        return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout

    return get_pcm_bytes(file1) == get_pcm_bytes(file2)


def export_track_file(src_file: str, dst_file: str, cover: str, album: Album, track: Track) -> None:
    """
    导出歌曲。
    """
    # flac 格式封面限制 16 MiB
    if Path(cover).stat().st_size >= 16 * 1024 * 1024:
        lprint(MESSAGE.LKO.format(cover))
        compress_img_by_pngquant(cover)
    
    shutil.copy2(src_file, dst_file)
    # tracknumber 为 0 时
    tn = str(track.tracknumber) if track.tracknumber else ""
    write_audio_tags(dst_file, 
                     cover, 
                     album.catalognumber, album.date, album.album, 
                     tn, track.title, track.artist)


def main() -> None:
    export_dir = easy_linput(MESSAGE.SOP, return_type=Path)
    
    kanban = KanBan(global_settings.metadata_directory, global_settings.resource_directory)

    total = sum(1 for tk in kanban.theme_kanbans for ak in tk.album_kanbans for t in ak.album.tracks if t.mark == "1")
    current = 0

    for theme_kanban in kanban.theme_kanbans:
        for album_kanban in theme_kanban.album_kanbans:
            album = album_kanban.album

            for i, track in enumerate(album.tracks):

                # 无资源时 或着 非 favourite 时 跳过
                if not album_kanban.track_files[i] or track.mark != "1":
                    continue

                current += 1

                src_file = Path(album_kanban.track_files[i])
                dst_file = Path(export_dir, os.path.basename(theme_kanban.theme_directory), legalize_filename(track.title)+src_file.suffix)
                dst_file.parent.mkdir(parents=True, exist_ok=True)

                # 目标不存在时 导出
                if not dst_file.exists():
                    lprint(MESSAGE.GFD.format(current, total, src_file, dst_file))
                    export_track_file(src_file, dst_file, album_kanban.cover, album, track)
                    continue

                # 通过 元数据+修改时间 判断是否相同
                tn = str(track.tracknumber) if track.tracknumber else ""
                src_values = (album.catalognumber, album.date, album.album, tn, track.title, track.artist)
                dst_values = tuple(read_audio_tags(dst_file, standard=True).values())
                is_metadata_same = src_values == dst_values and src_file.stat().st_mtime < dst_file.stat().st_mtime
                logger.debug(f"is_metadata_same: {is_metadata_same}, src_values: {src_values}, dst_values: {dst_values}")

                # 通过 音频解码数据 判断是否相同
                if is_metadata_same or is_audios_same(src_file, dst_file):
                    lprint(MESSAGE.RE5.format(current, total, dst_file))
                    continue

                # 确认覆盖
                if easy_linput(MESSAGE.BN8.format(src_file, dst_file), default="N", return_type=str)  == "Y":
                    lprint(MESSAGE.GFD.format(current, total, src_file, dst_file))
                    export_track_file(src_file, dst_file, album_kanban.cover, album, track)
                    continue
                

