import json
import os
import itertools
import subprocess

from src.core.logger import logger


def run_subprocess(cmd: list[str], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text: bool = False, **kwargs
                    ) -> subprocess.CompletedProcess:
    """
    封装 subprocess.run 。
    1. 在执行命令的前后、进程错误时打印日志。
    2. 检查进程返回值是否为 0 。
    """
    logger.debug(f"Begin to run cmd. {cmd}")
    process = subprocess.run(cmd, stdout=stdout, stderr=stderr, 
                             text=text, encoding=("utf-8" if text else None), **kwargs)
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
    ffmpeg_path = os.path.abspath(os.path.join("bin", "ffmpeg.exe"))
    cmd = [ffmpeg_path, "-i", audio_path, "-f", "s16le", "-"]
    process = run_subprocess(cmd)
    return process.stdout


def show_audio_stream_info(audio_path: str) -> dict:
    logger.info(f"Show audio stream info. {audio_path}")
    ffprobe_path = os.path.abspath(os.path.join("bin", "ffprobe.exe"))
    cmd = [ffprobe_path, "-v", "quiet", "-print_format", "json", "-show_streams", "-select_streams", "a", audio_path]
    process = run_subprocess(cmd, text=True)
    return json.loads(process.stdout)


def compress_image(img_path: str) -> None:
    logger.info(f"Compress image. {img_path}")
    pngquant_path = os.path.abspath(os.path.join("bin", "pngquant.exe"))
    cmd = [pngquant_path, "--force", "--output", img_path, "--", img_path]
    run_subprocess(cmd)


def rar_archive(dstrar: str, srcdir: str, password: str = "") -> None:
    """
    压缩文件夹。

    :param dstrar: 目标压缩包路径
    :param srcdir: 源文件夹路径
    :param password: 密码
    
    -@      禁用文件列表
    -ams    保留压缩文件元数据
    -cfg-   忽略默认配置文件和环境变量
    -m0     仅压缩
    -qo+    添加快速打开信息
    -r      包含子文件
    -rr5    添加 5% 数据恢复记录。加密时才有恢复记录。
    -scf    UTF-8 字符集
    -s-     禁用固实压缩
    -tk     保留原始压缩时间
    -ts     保存文件时间
    """
    if not os.path.isdir(srcdir):
        raise NotADirectoryError(f"path is not a directory. {srcdir}")
    
    srcdir, dstrar = os.path.abspath(srcdir), os.path.abspath(dstrar)
    logger.info(f"Archive to rar. {srcdir} -> {dstrar}")

    rar_path = os.path.abspath(os.path.join("bin", "WinRAR", "Rar.exe"))
    cmd = ([rar_path, "a", "-@", "-ams", "-cfg-", "-m0", "-r", "-rr5", "-qo+", "-scf", "-s-", "-ts", "-tk"] + 
           [f"-p{password}"]*bool(password) + 
           [dstrar, "*"])
    run_subprocess(cmd, cwd=srcdir, text=True)


def rar_add(dstrar: str, srcfiles: list[str], password: str = "") -> None:
    """
    添加文件到压缩包。
    将会覆盖压缩包里已存在的同名文件。

    :param dstrar: 目标压缩包路径
    :param srcpath: 源文件路径列表
    :param password: 密码

    -ep     添加文件但不包含路径信息
    """
    if not all(map(os.path.isfile, srcfiles)):
        raise FileNotFoundError(f"path is not a file. {srcfiles}")
    
    srcfiles, dstrar = list(map(os.path.abspath, srcfiles)), os.path.abspath(dstrar)
    logger.info(f"Add to rar. {srcfiles} -> {dstrar}")

    rar_path = os.path.abspath(os.path.join("bin", "WinRAR", "Rar.exe"))
    cmd = ([rar_path, "a", "-@", "-ams", "-cfg-", "-ep", "-m0", "-rr5", "-qo+", "-scf", "-s-", "-ts", "-tk"] + 
           [f"-p{password}"]*bool(password) + 
           [dstrar] + srcfiles)
    run_subprocess(cmd)


def rar_rename(dstrar: str, oldnames: list[str], newnames: list[str]) -> None:
    """
    重命名压缩包内的文件。

    :param dstrar: 目标压缩包路径
    :param oldname: 旧文件名列表
    :param newname: 新文件名列表
    """
    if len(oldnames) != len(newnames) or not newnames:
        raise ValueError(f"two list are not equal in length. {oldnames} {newnames}")
    
    dstrar = os.path.abspath(dstrar)
    logger.info(f"Rename rar files. {dstrar} {oldnames} -> {newnames}")

    rar_path = os.path.abspath(os.path.join("bin", "WinRAR", "Rar.exe"))
    cmd = [rar_path, "rn", dstrar, *list(itertools.chain.from_iterable(zip(oldnames, newnames)))]
    run_subprocess(cmd)


def rar_list(dstrar: str) -> list[str]:
    """
    列出压缩包内的文件。

    :param dstrar: 目标压缩包路径
    :param filename: 文件名
    """
    dstrar = os.path.abspath(dstrar)
    logger.info(f"List rar files. {dstrar}")

    rar_path = os.path.abspath(os.path.join("bin", "WinRAR", "Rar.exe"))
    cmd = [rar_path, "lb", dstrar]
    process = run_subprocess(cmd, text=True)
    files = [l for l in process.stdout.split("\n") if l]
    logger.debug(f"files: {files}")
    return files


def rar_read(dstrar: str, filename: str, password: str = "") -> bytes:
    """
    读取压缩包内的文件。

    :param dstrar: 目标压缩包路径
    :param filename: 文件名
    :param password: 密码
    """
    dstrar = os.path.abspath(dstrar)
    logger.info(f"Read rar file. {dstrar} {filename}")

    rar_path = os.path.abspath(os.path.join("bin", "WinRAR", "Rar.exe"))
    cmd = ([rar_path, "p"] + 
           [f"-p{password}"]*bool(password) + 
           [dstrar, filename])
    process = run_subprocess(cmd)
    return process.stdout

