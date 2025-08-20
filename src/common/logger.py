import os
import logging
import time
from functools import wraps
from typing import Callable


def _get_logger(level: int = logging.INFO) -> logging.Logger:

    # 抑制其他库的日志输出
    logging.getLogger().setLevel(logging.WARNING)

    logger = logging.getLogger("ongaku")

    logger.setLevel(level)

    fmt= "[%(asctime)s][%(levelname)s] %(message)s [%(funcName)s, %(filename)s, line %(lineno)d][process %(process)d, thread %(thread)d]"
    formatter = logging.Formatter(fmt)

    # ONGAKU_TMP_PATH 影响日志输出位置
    # 附加到 文件
    if tmp_path:= os.getenv("ONGAKU_TMP_PATH"):
        file_handler = logging.FileHandler(os.path.join(tmp_path, "ongaku.log"), "w", encoding="utf_8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    # 附加到 sys.stderr
    else:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    return logger


logger = _get_logger()


def logger_watched(level: int) -> Callable:
    """
    函数出入口日志打印装饰器。
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


