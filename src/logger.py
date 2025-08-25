import os
import logging
import time
from functools import wraps
from typing import Callable
from datetime import datetime


class OngakuLogger:

    def __init__(self, level: int = logging.INFO, outfile: str = None) -> None:

        # 抑制其他库的日志输出
        logging.getLogger().setLevel(logging.WARNING)

        self.logger = logging.getLogger("ongaku")
        self.logger.setLevel(level)

        fmt= "[%(asctime)s][%(levelname)s] %(message)s [%(funcName)s, %(filename)s, line %(lineno)d][process %(process)d, thread %(thread)d]"
        self.formatter = logging.Formatter(fmt)

        self.outfile = outfile
        # TODO: 环境变量 ？
        if not self.outfile:
            tmp_path = os.getenv("ONGAKU_TMP_PATH")
            if tmp_path: self.outfile = os.path.join(tmp_path, "ongaku.log")

        self._set_handler()

    def set_outfile(self, anypath: str = None) -> None:
        """
        重新设置日志输出文件位置。\n
        :param anypath: None, 文件或目录
        """
        if not anypath:
            self.outfile = None
        elif os.path.isfile(anypath):
            self.outfile = anypath
        elif os.path.isdir(anypath):
            name = f"{datetime.now().strftime("%Y-%d-%m-%H-%M-%S")}.log"
            self.outfile = os.path.join(anypath, name)

        self._set_handler()

    # 内部方法

    def _set_handler(self) -> None:
        # 清空 handlers
        for h in list(self.logger.handlers):
            self.logger.removeHandler(h)
            h.close()

        if self.outfile:
            handler = logging.FileHandler(self.outfile, "a", encoding="utf-8")
        else:
            handler = logging.StreamHandler()

        handler.setFormatter(self.formatter)
        self.logger.addHandler(handler)


_ongaku_logger = OngakuLogger()
logger = _ongaku_logger.logger


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


