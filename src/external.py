import itertools
import json
import os
import re
import subprocess
import sys
import tempfile
from typing import Union

from src.core.logger import logger


def run_subprocess(cmd: list[str], stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                   check: bool = True, encoding: str = None, **kwargs
                   ) -> subprocess.CompletedProcess:
    """
    封装 subprocess.run 。
    1. 在执行命令的前后、进程错误时打印日志。
    2. 检查进程返回值是否为 0 。
    """
    logger.debug(f"Begin to run cmd. {cmd}")

    # Windows 下不弹出窗口
    if sys.platform == "win32":
        info = subprocess.STARTUPINFO()
        info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = subprocess.SW_HIDE
    else:
        info = None

    # subprocess.Popen cwd 参数输入长路径（大于 256 字符），会抛出 NotADirectoryError
    # 临时目录联接
    tmpdir = None
    if isinstance((cwd:= kwargs.get("cwd")), str):
        if len(cwd) >= 257:
            tmpdir = tempfile.TemporaryDirectory(prefix="run_subprocess_")
            d = os.path.join(tmpdir.name, "_")
            os.symlink(cwd, d, target_is_directory=True)
            kwargs["cwd"] = d
            logger.info(f"Parameter cwd exceeds 256 characters, replace it with a temp directory. {len(cwd)} {cwd}.")

    try:
        process = subprocess.run(cmd, stdout=stdout, stderr=stderr, check=check, 
                                 encoding=encoding, startupinfo=info, **kwargs)
    except subprocess.CalledProcessError as e:
        if encoding:
            logger.debug(f"stdout: {e.stdout}")
            logger.debug(f"stderr: {e.stderr}")
        logger.error(f"Failed to run cmd. {cmd}", exc_info=1)
        raise
    finally:
        tmpdir and tmpdir.cleanup()

    logger.info(f"Succeed to run cmd. {cmd}")
    return process


################################################################################
### FFMpeg
### https://www.ffmpeg.org/documentation.html
################################################################################

def decode_audio_bytes_to_pcm(audio_data: bytes) -> bytes:
    """
    解码音频为裸 PCM 数据。

    -f s16le    signed 16-bit little-endian PCM
    """
    if not audio_data:
        logger.info(f"Empty audio data.")
        return b""

    logger.info(f"Decode audio data to pcm. {len(audio_data)} bytes")
    ffmpeg_path = os.path.abspath(os.path.join("bin", "ffmpeg.exe"))
    cmd = [ffmpeg_path, "-i", "pipe:0", "-f", "s16le", "-"]
    process = run_subprocess(cmd, input=audio_data)
    return process.stdout


def convert_audio_bytes_to_wav(audio_data: bytes) -> bytes:
    """
    转码音频数据为 WAV 数据。
    """
    if not audio_data:
        logger.info(f"Empty audio data.")
        return b""
    
    logger.info(f"Convert audio data to wav data. {len(audio_data)} bytes")
    ffmpeg_path = os.path.abspath(os.path.join("bin", "ffmpeg.exe"))
    cmd = [ffmpeg_path, "-i", "pipe:0", "-f", "wav", "-"]
    process = run_subprocess(cmd, input=audio_data)
    return process.stdout


def show_audio_stream_info(audio_input: Union[str, bytes]) -> dict:
    """
    获取音频流信息。

    :param audio_input: str 类型的音频文件路径，或者 bytes 类型的音频字节数据
    """
    if not isinstance(audio_input, (str, bytes)):
        raise TypeError(f"audio_input is not str or bytes. {type(audio_input)}")
    if not audio_input:
        raise ValueError(f"Empty audio_input.")

    is_path = isinstance(audio_input, str)
    logger.info(f"Show audio stream info. {audio_input if is_path else ''}")
    ffprobe_path = os.path.abspath(os.path.join("bin", "ffprobe.exe"))
    if is_path:
        cmd = [ffprobe_path, "-v", "quiet", "-print_format", "json", "-show_streams", "-select_streams", "a", audio_input]
        process = run_subprocess(cmd)
    else:
        cmd = [ffprobe_path, "-i", "pipe:0", "-v", "quiet", "-print_format", "json", "-show_streams", "-select_streams", "a"]
        process = run_subprocess(cmd, input=audio_input)
    return json.loads(process.stdout)


def calculate_audio_md5(audio_input: Union[str, bytes]) -> str:
    """
    计算音频流 md5。

    :param audio_input: str 类型的音频文件路径，或者 bytes 类型的音频字节数据
    """
    if not isinstance(audio_input, (str, bytes)):
        raise TypeError(f"audio_input is not str or bytes. {type(audio_input)}")
    if not audio_input:
        raise ValueError(f"Empty audio_input.")

    is_path = isinstance(audio_input, str)
    logger.info(f"Calculate audio md5. {audio_input if is_path else ''}")
    ffmpeg_path = os.path.abspath(os.path.join("bin", "ffmpeg.exe"))
    if is_path:
        cmd = [ffmpeg_path, "-i", audio_input, "-map", "0:a", "-c", "copy", "-f", "md5", "-"]
        process = run_subprocess(cmd)
    else:
        cmd = [ffmpeg_path, "-i", "pipe:0", "-map", "0:a", "-c", "copy", "-f", "md5", "-"]
        process = run_subprocess(cmd, input=audio_input)
    return process.stdout.decode("utf-8")


################################################################################
### PNGQuant
### https://pngquant.org/
################################################################################

def compress_png_file(png_path: str) -> None:
    """
    原位置压缩 png 文件。
    """
    logger.info(f"Compress png. {png_path}")
    pngquant_path = os.path.abspath(os.path.join("bin", "pngquant.exe"))
    cmd = [pngquant_path, "--force", "--output", png_path, "--", png_path]
    run_subprocess(cmd)


################################################################################
### WinRAR
################################################################################

def rar_archive(dstrar: str, srcdir: str) -> None:
    """
    压缩文件夹。

    :param dstrar: 目标压缩包路径
    :param srcdir: 源文件夹路径
    
    a       添加文件到压缩文件中
    -@      禁用文件列表
    -ams    保留压缩文件元数据
    -cfg-   忽略默认配置文件和环境变量
    -m0     仅压缩
    -qo+    添加快速打开信息
    -r      包含子文件
    -rr5    添加 5% 数据恢复记录。加密时才有恢复记录。
    -scf    UTF-8 字符集
    -s-     禁用固实压缩
    -ts     保存文件时间
    """
    if not os.path.isdir(srcdir):
        raise NotADirectoryError(f"path is not a directory. {srcdir}")
    
    srcdir, dstrar = os.path.abspath(srcdir), os.path.abspath(dstrar)
    logger.info(f"Archive to rar. {srcdir} -> {dstrar}")

    rar_path = os.path.abspath(os.path.join("bin", "WinRAR", "Rar.exe"))
    cmd = ([rar_path, "a", "-@", "-ams", "-cfg-", "-m0", "-r", "-rr5", "-qo+", "-scf", "-s-", "-ts"] + 
           [dstrar, "*"])
    run_subprocess(cmd, cwd=srcdir)


def rar_add(dstrar: str, srcfiles: list[str]) -> None:
    """
    添加文件到压缩包。
    将会覆盖压缩包里已存在的同名文件。

    :param dstrar: 目标压缩包路径
    :param srcpath: 源文件路径列表

    -ep     添加文件但不包含路径信息。扁平。
    """
    if not all(map(os.path.isfile, srcfiles)):
        raise FileNotFoundError(f"path is not a file. {srcfiles}")
    
    srcfiles, dstrar = list(map(os.path.abspath, srcfiles)), os.path.abspath(dstrar)
    logger.info(f"Add to rar. {srcfiles} -> {dstrar}")

    rar_path = os.path.abspath(os.path.join("bin", "WinRAR", "Rar.exe"))
    cmd = ([rar_path, "a", "-@", "-ams", "-cfg-", "-ep", "-m0", "-rr5", "-qo+", "-scf", "-s-", "-ts"] + 
           [dstrar] + srcfiles)
    run_subprocess(cmd)


def rar_rename(dstrar: str, oldnames: list[str], newnames: list[str]) -> None:
    """
    重命名压缩包内的文件。

    :param dstrar: 目标压缩包路径
    :param oldname: 旧文件名列表
    :param newname: 新文件名列表

    rn      重命名压缩文件
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
    :return filenames: 文件名列表。

    lb       压缩文件的内容列表
    -scf     指定 UTF-8 字符集
    """
    dstrar = os.path.abspath(dstrar)
    logger.info(f"List rar files. {dstrar}")

    rar_path = os.path.abspath(os.path.join("bin", "WinRAR", "Rar.exe"))
    cmd = [rar_path, "lb", "-scf", dstrar]
    process = run_subprocess(cmd, encoding="utf-8")
    files = [l for l in process.stdout.split("\n") if l]
    logger.debug(f"files: {files}")
    return files


def rar_read(dstrar: str, filename: str) -> bytes:
    """
    读取压缩包内的文件。

    :param dstrar: 目标压缩包路径
    :param filename: 文件名。为空时将会返回空字节。

    p       打印文件到标准输出设备
    """
    dstrar = os.path.abspath(dstrar)
    logger.info(f"Read rar file. {dstrar} {filename}")

    if not filename:
        return b""

    rar_path = os.path.abspath(os.path.join("bin", "WinRAR", "Rar.exe"))
    cmd = ([rar_path, "p", dstrar, filename])
    process = run_subprocess(cmd)
    return process.stdout


def rar_delete(dstrar: str, filename: str) -> None:
    """
    删除压缩包内的文件。

    :param dstrar: 目标压缩包路径
    :param filename: 文件名。为空时将会直接返回。

    d       从压缩文件中删除文件
    """
    dstrar = os.path.abspath(dstrar)
    logger.info(f"Delete rar file. {dstrar} {filename}")

    if not filename:
        return

    rar_path = os.path.abspath(os.path.join("bin", "WinRAR", "Rar.exe"))
    cmd = ([rar_path, "d", dstrar, filename])
    run_subprocess(cmd)


_NAME_PAT = re.compile(r"^\s+名称:\s+(.+)$", re.MULTILINE)
_SIZE_PAT = re.compile(r"^\s+大小:\s+(\d+)$", re.MULTILINE)


def rar_stats(dstrar: str) -> dict[str, os.stat_result]:
    """
    统计压缩包内的文件属性。

    :param dstrar: 目标压缩包路径

    :return stats: 仅填充 stat_result.st_size 。

    lt       显示详细的文件信息
    -scf     指定 UTF-8 字符集
    """
    dstrar = os.path.abspath(dstrar)
    logger.info(f"Stat rar file. {dstrar}")

    rar_path = os.path.abspath(os.path.join("bin", "WinRAR", "Rar.exe"))
    cmd = [rar_path, "lt", "-scf", dstrar]
    process = run_subprocess(cmd, encoding="utf-8")

    _dict = {}
    for s in process.stdout.split("\n\n"):
        name = _NAME_PAT.search(s)
        size = _SIZE_PAT.search(s)

        if name and size:
            _dict[name.group(1)] = os.stat_result((0,)*6 + (int(size.group(1)),) + (0,)*3)

    logger.debug(f"stats: {_dict}")
    return _dict


def rar_extract(dstrar: str, filename: str, savedir: str) -> None:
    """
    提取压缩包内的文件。
    filename 为空时将直接返回。

    :param dstrar: 目标压缩包路径
    :param filename: 文件名
    :param savedir: 保存目录

    e       不带压缩路径解压文件
    """
    dstrar = os.path.abspath(dstrar)
    logger.info(f"Extract rar file. {dstrar} {filename} {savedir}")

    if not filename:
        return

    rar_path = os.path.abspath(os.path.join("bin", "WinRAR", "Rar.exe"))
    cmd = ([rar_path, "e", dstrar, filename, savedir])
    run_subprocess(cmd)


################################################################################
### PostgreSQL
### https://www.postgresql.org/docs/current/index.html
################################################################################

def init_pgdata(pgdata: str) -> None:
    """
    初始化 PostgreSQL 数据目录。

    :param pgdata: 数据目录

    --auth=trust        local trust
    --encoding=UTF8     数据库编码
    --no-locale         相当于 --locale=C ，与具体语言和地域无关的默认区域设置
    --nosync            不等待文件安全写入磁盘
    --username=postgres 超级用户名
    """
    pgdata = os.path.abspath(pgdata)
    logger.info(f"Init pgdata. {pgdata}")

    initdb_exe = os.path.abspath(os.path.join("bin", "pgsql", "bin", "initdb.exe"))
    cmd = [initdb_exe, "--auth=trust", "--encoding=UTF8", "--no-locale", "--nosync", 
           "--username=postgres", "-D", pgdata]
    run_subprocess(cmd, encoding="utf-8")


def pg_ctl_start(pgdata: str) -> None:
    """
    启动 PostgreSQL 数据库。

    :param pgdata: 数据目录

    --silent        只打印错误
    """
    pgdata = os.path.abspath(pgdata)
    logger.info(f"Start postgres. {pgdata}")

    pg_ctl_exe = os.path.abspath(os.path.join("bin", "pgsql", "bin", "pg_ctl.exe"))
    cmd = [pg_ctl_exe, "--silent", "-D", pgdata, "start"]
    run_subprocess(cmd, encoding="utf-8")


def pg_ctl_stop(pgdata: str) -> None:
    """
    停止 PostgreSQL 数据库。

    :param pgdata: 数据目录

    --silent        只打印错误
    """
    pgdata = os.path.abspath(pgdata)
    logger.info(f"Stop postgres. {pgdata}")

    pg_ctl_exe = os.path.abspath(os.path.join("bin", "pgsql", "bin", "pg_ctl.exe"))
    cmd = [pg_ctl_exe, "--silent", "-D", pgdata, "stop"]
    run_subprocess(cmd, encoding="utf-8")


def pg_dump_database(dbname: str, dmpfile: str) -> None:
    """
    备份 PostgreSQL 数据库。

    :param dbname: 数据库名
    :param dmpfile: 转储文件路径

    -Upostgres  用户名
    -Fc         自定义格式的归档文件
    """
    dmpfile = os.path.abspath(dmpfile)
    logger.info(f"pg_dump database. {dbname} {dmpfile}")

    pg_dump_exe = os.path.abspath(os.path.join("bin", "pgsql", "bin", "pg_dump.exe"))
    cmd = [pg_dump_exe, "-Upostgres", "-Fc", "-f", dmpfile, dbname]
    run_subprocess(cmd, encoding="utf-8")


################################################################################
### Windows
### https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/windows-commands
################################################################################

def open_in_explorer(path: str) -> None:
    """
    在资源管理器中打开文件夹或选中文件。

    :param path: 文件或文件夹
    """
    if os.path.isfile(path):
        cmd = f'explorer /select,"{path}"'
    elif os.path.isdir(path):
        cmd = f'explorer "{path}"'
    else:
        raise FileNotFoundError(path)

    run_subprocess(cmd, check=False, shell=True)


def copy_to_clipboard(text: str) -> None:
    """
    粘贴文本至 Windows 剪贴板。
    """
    cmd = ["clip"]
    run_subprocess(cmd, encoding="utf-8", input=text)


################################################################################
### 衍生
################################################################################

def calculate_rar_audio_md5(dstrar: str, filename: str) -> str:
    """
    计算压缩包内的音频流 md5。
    """
    return calculate_audio_md5(rar_read(dstrar, filename))


