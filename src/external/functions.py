import os
import json
import subprocess

from src.core.logger import logger


def run_subprocess(cmd: str, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text: bool = False
                    ) -> subprocess.CompletedProcess:
    """
    封装 subprocess.run 。在执行命令的前后、进程错误时打印日志。
    """
    logger.debug(f"Begin to run cmd. {cmd}")
    process = subprocess.run(cmd, stdout=stdout, stderr=stderr, text=text)
    if process.returncode == 0:
        logger.info(f"Succeed to run cmd. {cmd}")
        return process

    if text:
        logger.debug(f"stdout: {process.stdout}")
        logger.debug(f"stderr: {process.stderr}")
    logger.info(f"Failed to run cmd. {cmd}")
    raise subprocess.CalledProcessError(process.returncode, cmd, process.stdout, process.stderr)


def decode_audio_to_pcm(audio_path: str) -> bytes:
    logger.info(f"Decode audio to pcm. {audio_path}")
    ffmpeg_path = os.path.join("bin", "ffmpeg.exe")
    cmd = f'{ffmpeg_path} -i "{audio_path}" -f s16le -'
    return run_subprocess(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def show_audio_stream_info(audio_path: str) -> dict:
    logger.info(f"Show audio stream info. {audio_path}")
    ffprobe_path = os.path.join("bin", "ffprobe.exe")
    cmd = f'{ffprobe_path} -v quiet -print_format json -show_streams -select_streams a "{audio_path}"'
    process = run_subprocess(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return json.loads(process.stdout)


def compress_image(img_path: str) -> None:
    logger.info(f"Compress image. {img_path}")
    pngquant_path = os.path.join("bin", "pngquant.exe")
    cmd = f'{pngquant_path} --force --output "{img_path}" -- "{img_path}"'
    run_subprocess(cmd)
