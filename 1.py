



import os
import subprocess
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from tqdm import tqdm




EXTRACT_COVER_CMD = '"{ffmpeg}" -i "{audio}" -map 0:v -c copy "{cover}"'
MAKE_VIDEO_CMD = '"{ffmpeg}" -loop 1 -framerate 2 -i "{cover}" -i "{audio}" -c:v libx264 -preset veryfast -tune stillimage -vf "scale=1280:-2" -pix_fmt yuv420p -c:a copy -shortest "{dst_audio}"'

AUDIO_EXTS = {".flac", ".mp3"}
IMAGE_EXT = ".png"
VIDEO_EXT = ".mkv"

if __name__ == "__main__":

    ffmpeg_path = r"E:\tool\ffmpeg\bin\ffmpeg.exe"
    src_dir = r"F:\ongaku-export\Artist\おでんぱ☆スタジオ [Odenpa Studio]"
    dst_dir = r"D:\新建文件夹"

    src_files = [f for f in Path(src_dir).rglob("*") if f.suffix.lower() in AUDIO_EXTS]

    for src_file in src_files:
        cover = Path(dst_dir, src_file.with_suffix(IMAGE_EXT).name)
        dst_file = Path(dst_dir, src_file.with_suffix(VIDEO_EXT).name)

        if dst_file.is_file() and dst_file.stat().st_size > 100:
            continue

        cover.is_file() and cover.unlink()
        dst_file.is_file() and dst_file.unlink()

        cmd1 = EXTRACT_COVER_CMD.format(ffmpeg=ffmpeg_path, audio=src_file, cover=cover)
        cmd2 = MAKE_VIDEO_CMD.format(ffmpeg=ffmpeg_path, audio=src_file, cover=cover, dst_audio=dst_file)

        future = subprocess.run(f"{cmd1} && {cmd2}", shell=True)




