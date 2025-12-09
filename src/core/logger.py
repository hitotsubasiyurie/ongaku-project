import os
import time
import gzip
import shutil
import logging
from functools import wraps
from datetime import datetime
from pathlib import Path
from typing import TextIO, Callable
from logging.handlers import RotatingFileHandler

from src.core.settings import global_settings


class CompressedRotatingFileHandler(RotatingFileHandler):
    """压缩转储"""

    def doRollover(self) -> None:
        if self.stream:
            self.stream.close()
            self.stream = None

        base_file = Path(self.baseFilename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated_file = base_file.with_name(f"{base_file.stem}_{timestamp}{base_file.suffix}")

        base_file.rename(rotated_file)
        with rotated_file.open("rb") as f_in:
            with gzip.open(str(rotated_file) + ".gz", "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        rotated_file.unlink()

        self.mode = "a"
        self.stream = self._open()


class WithRawFormatter(logging.Formatter):
    """生打印格式化"""

    IN_RAW_KEY = "IS_IN_RAW"

    def __init__(self, fmt: str) -> None:
        super().__init__(fmt)
        self.raw_formatter = logging.Formatter("%(message)s")

    def format(self, record: logging.LogRecord) -> str:
        if getattr(record, WithRawFormatter.IN_RAW_KEY, False):
            return self.raw_formatter.format(record)
        return super().format(record)


class OngakuLogger:

    LOGGER_NAME = "ongaku"
    MAX_LOG_FILE_SIZE = 10 * 1024 * 1024

    def __init__(self, level: int = logging.INFO, outfile: str = None) -> None:

        # 抑制其他库的日志输出
        logging.getLogger().setLevel(logging.WARNING)

        self.logger = logging.getLogger(OngakuLogger.LOGGER_NAME)
        self.logger.setLevel(level)

        fmt= "[%(asctime)s][%(levelname)s] %(message)s [%(funcName)s, %(filename)s, line %(lineno)d][process %(process)d, thread %(thread)d]"
        self.formatter = WithRawFormatter(fmt)

        self.outfile = outfile

        self._set_handler()

    def set_output(self, anypath: str = None) -> None:
        """
        重新设置日志输出文件位置。\n
        :param anypath: None、文件、目录
        """
        if not anypath or not os.path.exists(anypath):
            self.outfile = None
        elif os.path.isfile(anypath):
            self.outfile = anypath
        elif os.path.isdir(anypath):
            self.outfile = os.path.join(anypath, f"{OngakuLogger.LOGGER_NAME}.log")

        self._set_handler()

    ######## 内部方法 ########

    def _set_handler(self) -> None:
        # 清空 handlers
        for h in list(self.logger.handlers):
            self.logger.removeHandler(h)
            h.close()

        if self.outfile:
            handler = CompressedRotatingFileHandler(self.outfile, mode="a", encoding="utf-8", 
                                                    maxBytes=OngakuLogger.MAX_LOG_FILE_SIZE)
        else:
            handler = logging.StreamHandler()

        handler.setFormatter(self.formatter)
        self.logger.addHandler(handler)


_ongaku_logger = OngakuLogger()

logger = _ongaku_logger.logger

# 设置 日志
os.makedirs(global_settings.temp_directory, exist_ok=True)
_ongaku_logger.set_output(global_settings.temp_directory)

_level_map = {1: logging.DEBUG, 2: logging.INFO, 3: logging.WARNING, 4: logging.ERROR, 5: logging.FATAL}
logger.setLevel(_level_map.get(global_settings.log_level, 2))


def lprint(*values: object, sep: str | None = " ", end: str | None = "\n", 
            file: TextIO | None = None, flush: bool = False) -> None:
    """
    print 函数，在调用之前先将内容原样写入日志文件。
    """
    s = sep.join(str(a) for a in values) + end
    logger.info(s, extra={WithRawFormatter.IN_RAW_KEY: True})

    print(*values, sep=sep, end=end, file=file, flush=flush)


def linput(prompt: object  = "") -> str:
    """
    input 函数，在调用之后将提示和输入原样写入日志文件。
    """
    s = input(prompt)
    logger.info(prompt + s + "\n", extra={WithRawFormatter.IN_RAW_KEY: True})

    return s


def logger_watched(level: int) -> Callable:
    """
    函数出入口日志打印装饰器。\n
    :param level: 缩进级别， [1, 5]
    """
    level = max(1, min(level, 5))

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.info(f"{'----' * level}> Start {func.__name__}.")
            st = time.time()
            result = func(*args, **kwargs)
            logger.info(f"{'----' * level}> End {func.__name__}, use {round(time.time() - st, 2)} s.")
            return result
        return wrapper
    
    return decorator


