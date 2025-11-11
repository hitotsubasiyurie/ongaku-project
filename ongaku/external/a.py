import json
import subprocess

from ongaku.core.logger import logger


def decode_audio_to_pcm(audio_path: str) -> bytes:
    ffmpeg_path = r".\bin\ffmpeg.exe"
    cmd = f'{ffmpeg_path} -i "{audio_path}" -f s16le -'
    logger.info(f"Decode audio to pcm. {cmd}")
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout


def show_audio_stream_info(audio_path: str) -> dict:
    ffprobe_path = r".\bin\ffprobe.exe"
    cmd = f'{ffprobe_path} -v quiet -print_format json -show_streams -select_streams a "{audio_path}"'
    logger.info(f"Show audio stream info. {cmd}")
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return json.loads(process.stdout)


def compress_image(img_path: str) -> None:
    pngquant_path = r".\bin\pngquant.exe"
    cmd = f'{pngquant_path} --force --output "{img_path}" -- "{img_path}"'
    logger.info(f"Compress image. {cmd}")
    subprocess.run(cmd, check=True)

