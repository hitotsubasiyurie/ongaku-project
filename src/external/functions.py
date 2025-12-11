import json
import os
import subprocess

from src.core.logger import logger


def run_subprocess(cmd: str, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text: bool = False, cwd: str = None
                    ) -> subprocess.CompletedProcess:
    """
    封装 subprocess.run 。
    1. 在执行命令的前后、进程错误时打印日志。
    2. 检查进程返回值是否为 0 。
    """
    logger.debug(f"Begin to run cmd. {cmd}")
    process = subprocess.run(cmd, stdout=stdout, stderr=stderr, cwd=cwd, text=text)
    if process.returncode == 0:
        logger.info(f"Succeed to run cmd. {cmd}")
        return process

    if text:
        logger.debug(f"stdout: {process.stdout}")
        logger.debug(f"stderr: {process.stderr}")
    logger.error(f"Failed to run cmd. {cmd}")
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


def rar_add(srcpath: str, dstrar: str, password: str = "") -> None:
    """
    添加文件到压缩包。
    将会覆盖压缩包里已存在的同名文件。

    :param srcpath: 源路径，文件或文件夹
    :param dstrar: 目标压缩包路径
    :param password: 密码。新增文件密码可以与原压缩包密码不一致。加密时才有恢复记录。
    
    -ams    保留压缩文件元数据
    -cfg-   忽略默认配置文件和环境变量
    -m0     仅压缩
    -qo+    添加快速打开信息
    -rr5    添加 5% 数据恢复记录
    -scf    UTF-8 字符集
    -s-     禁用固实压缩
    -tk     保留原始压缩时间
    -ts     保存文件时间
    """
    if not os.path.exists(srcpath):
        raise FileNotFoundError(f"srcpath not exist. {srcpath}")
    srcpath, dstrar = os.path.abspath(srcpath), os.path.abspath(dstrar)

    rar_path = os.path.join("bin", "WinRAR", "WinRAR.exe")
    cmd = (f'"{rar_path}" a -ams -cfg- -m0 -rr5 -qo+ -scf -s- -ts -tk' + 
           f" -p{password}"*bool(password) + 
           f' "{dstrar}"' + 
           (f' "{srcpath}"' if os.path.isfile(srcpath) else " *"))
    cwd = srcpath if os.path.isdir(srcpath) else os.path.dirname(srcpath)
    run_subprocess(cmd, cwd=cwd)


def rar_rename(dstrar: str, oldname: str, newname: str) -> None:
    """
    重命名压缩包内的文件。

    :param dstrar: 目标压缩包路径
    :param oldname: 
    :param newname: 
    """
    rar_path = os.path.join("bin", "WinRAR", "WinRAR.exe")
    cmd = f'"{rar_path}" rn "{dstrar}" "{oldname}" "{newname}"'
    run_subprocess(cmd)


def rar_list(dstrar: str) -> list[str]:
    """
    列出压缩包内的文件。

    :param dstrar: 目标压缩包路径
    :param filename: 文件名
    """
    rar_path = os.path.join("bin", "WinRAR", "Rar.exe")
    cmd = f'"{rar_path}" lb "{dstrar}"'
    process = run_subprocess(cmd, text=True)
    files = [l for l in process.stdout.split("\n") if l]
    return files

def rar_read(dstrar: str, filename: str, password: str = "") -> bytes:
    """
    读取压缩包内的文件。

    :param dstrar: 目标压缩包路径
    :param filename: 文件名
    :param password: 密码
    """
    rar_path = os.path.join("bin", "WinRAR", "Rar.exe")
    cmd = (f'"{rar_path}" p' + 
           f" -p{password}"*bool(password) + 
           f' "{dstrar}" "{filename}"')
    process = run_subprocess(cmd)
    return process.stdout


