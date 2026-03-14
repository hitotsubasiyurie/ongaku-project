import hashlib
import os
from typing import Callable, Any

from diskcache import Cache

from src.core.settings import g_settings

g_cache = Cache(
    os.path.join(g_settings.TMP_DIRECTORY, "cache"), 
    # 50 MiB 上限
    size_limit=50*1024*1024
)

g_request_cache = Cache(
    os.path.join(g_settings.TMP_DIRECTORY, "request_cache"), 
    # 50 MiB 上限
    size_limit=50*1024*1024
)


def full_name(func: Callable) -> str:
    """
    通过添加模块和函数名计算 func 的全名。
    """
    return func.__module__ + '.' + func.__name__


def make_key(*args) -> str:
    key = ":".join(str(a) for a in args)
    return hashlib.md5(key.encode()).hexdigest()


def with_cache(func: Callable, *args, related_file: str = "") -> Any:
    """
    :param related_file: 关联的文件。会使用 os.path.normpath 标准化路径
    """
    # 实现参考 diskcache.core.memoize
    func_name = full_name(func)
    if related_file:
        related_file = os.path.normpath(related_file)
        stat = os.stat(related_file)
        key = make_key(func_name, *args, related_file, stat.st_mtime, stat.st_size)
    else:
        key = make_key(func_name, *args)

    result = g_cache.get(key)
    if result is None:
        result = func(*args)
        g_cache.set(key, result)

    return result






