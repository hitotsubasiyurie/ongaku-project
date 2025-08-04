import time
from functools import wraps
from pathlib import Path
from threading import Lock
from typing import Callable, Generator

from ongaku.logger import logger


def retry(retries: int = 3, delay: int | float = 2) -> Callable:
    """
    重试装饰器。
    :param retries: 重试次数
    :param delay: 重试间隔
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while attempt < retries:
                attempt and logger.info(f"Retry the {attempt}th times.")
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    time.sleep(delay)
                    if attempt == retries:
                        raise e
            return None
        return wrapper
    return decorator


class RateLimiter:
    """函数调用频率限制装饰器。"""

    def __init__(self, interval: int | float) -> None:
        self._interval = interval
        self._last_call = 0
        self._lock = Lock()

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self._lock:
                if 0 < (wait:= self._last_call + self._interval - time.time()):
                    time.sleep(wait)
                self._last_call = time.time()
            return func(*args, **kwargs)
        
        return wrapper


def legalize_filename(name: str) -> str:
    """
    用全角符号替换路径中的非法符号。路径结尾无空格。
    :param name: 文件名
    """
    name = str(name)
    for i, j in zip(r'\/:*?"<>|', "＼／：＊？＂＜＞｜"):
        name = name.replace(i, j)
        name = name.rstrip()
    return name


def watch_file(filepath: str) -> Generator[int, None, None]:
    """
    监控文件变化。
    """
    file = Path(filepath)
    if not file.is_file():
        logger.error(f"File to be watched not exists. {filepath}")
        return None

    mtime = 0
    while True:
        if file.stat().st_mtime == mtime:
            time.sleep(1)
            continue
        yield 1
        mtime = file.stat().st_mtime



