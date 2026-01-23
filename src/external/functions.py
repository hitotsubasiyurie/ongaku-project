import json
import os
import re
import sys
import itertools
import subprocess
import tempfile

from src.core.logger import logger


def run_subprocess(cmd: list[str], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text: bool = False, **kwargs
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
            make_junction(cwd, d)
            kwargs["cwd"] = d
            logger.info("cwd too long, replace it with a temp directory.")

    try:
        process = subprocess.run(cmd, stdout=stdout, stderr=stderr, check=True, 
                                 text=text, startupinfo=info, **kwargs)
    except subprocess.CalledProcessError as e:
        if text:
            logger.debug(f"stdout: {e.stdout}")
            logger.debug(f"stderr: {e.stderr}")
        logger.error(f"Failed to run cmd. {cmd}")
        raise
    finally:
        tmpdir and tmpdir.cleanup()

    logger.info(f"Succeed to run cmd. {cmd}")
    return process


def decode_audio_to_pcm(audio_path: str) -> bytes:
    """
    解码音频为裸 PCM 数据。

    -f s16le    signed 16-bit little-endian PCM
    """
    logger.info(f"Decode audio to pcm. {audio_path}")
    ffmpeg_path = os.path.abspath(os.path.join("bin", "ffmpeg.exe"))
    cmd = [ffmpeg_path, "-i", audio_path, "-f", "s16le", "-"]
    process = run_subprocess(cmd)
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


def make_junction(srcdir: str, dstdir: str) -> None:
    """
    创建 Windows 目录联接。
    /c      执行完立刻退出
    /J      目录联接
    """
    os.makedirs(dstdir, exist_ok=True)
    logger.info(f"Make junction. {srcdir} -> {dstdir}")
    cmd = ["cmd", "/c", "mklink", "/J", dstdir, srcdir]
    run_subprocess(cmd)


def rar_archive(dstrar: str, srcdir: str) -> None:
    """
    压缩文件夹。

    :param dstrar: 目标压缩包路径
    :param srcdir: 源文件夹路径
    
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

    -scf     指定 UTF-8 字符集
    """
    dstrar = os.path.abspath(dstrar)
    logger.info(f"List rar files. {dstrar}")

    rar_path = os.path.abspath(os.path.join("bin", "WinRAR", "Rar.exe"))
    cmd = [rar_path, "lb", "-scf", dstrar]
    process = run_subprocess(cmd, text=True, encoding="utf-8")
    files = [l for l in process.stdout.split("\n") if l]
    logger.debug(f"files: {files}")
    return files


def rar_read(dstrar: str, filename: str) -> bytes:
    """
    读取压缩包内的文件。
    文件名为空或不存在时将会抛异常。

    :param dstrar: 目标压缩包路径
    :param filename: 文件名
    """
    if not filename:
        raise ValueError(f"Empty filename.")
    
    dstrar = os.path.abspath(dstrar)
    logger.info(f"Read rar file. {dstrar} {filename}")

    rar_path = os.path.abspath(os.path.join("bin", "WinRAR", "Rar.exe"))
    cmd = ([rar_path, "p", dstrar, filename])
    process = run_subprocess(cmd)
    return process.stdout


_NAME_PAT = re.compile(r"^\s+名称:\s+(.+)$", re.MULTILINE)
_SIZE_PAT = re.compile(r"^\s+大小:\s+(\d+)$", re.MULTILINE)


def rar_stats(dstrar: str, filenames: list[str]) -> list[os.stat_result | None]:
    """
    统计压缩包内的文件属性。
    文件名为空或者不存在时对应的 stat 为 None 。

    :param dstrar: 目标压缩包路径
    :param filenames: 文件名列表。

    :return stats: 仅填充 stat_result.st_size 。

    -scf     指定 UTF-8 字符集
    """
    dstrar = os.path.abspath(dstrar)
    logger.info(f"Stat rar file. {dstrar} {filenames}")

    rar_path = os.path.abspath(os.path.join("bin", "WinRAR", "Rar.exe"))
    cmd = [rar_path, "lt", "-scf", dstrar]
    process = run_subprocess(cmd, text=True, encoding="utf-8")

    _dict = {}
    for s in process.stdout.split("\n\n"):
        name = _NAME_PAT.search(s)
        size = _SIZE_PAT.search(s)

        if name and size:
            _dict[name.group(1)] = os.stat_result((0,)*6 + (int(size.group(1)),) + (0,)*3)

    stats = [_dict.get(n) for n in filenames]
    logger.debug(f"stats: {stats}")
    return stats


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
    run_subprocess(cmd, text=True)


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
    run_subprocess(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)


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
    run_subprocess(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)


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
    run_subprocess(cmd, text=True)


