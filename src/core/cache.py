import os
from typing import Callable, Any

from diskcache import Cache
from diskcache.core import args_to_key

from src.core.settings import settings

cache = Cache(os.path.join(settings.TMP_DIRECTORY, "cache"), size_limit=50*1024*1024)

request_cache = Cache(os.path.join(settings.TMP_DIRECTORY, "request_cache"), size_limit=100*1024*1024)


def _full_name(func: Callable) -> str:
    """
    通过添加模块和函数名计算 func 的全名。
    """
    return func.__module__ + '.' + func.__name__


def with_cache(func: Callable, *args, related_file: str = "") -> Any:
    """
    :param related_file: 关联的文件。会使用 os.path.normpath 标准化路径
    """
    # 实现参考 diskcache.core.memoize
    base = (_full_name(func),)
    if related_file:
        related_file = os.path.normpath(related_file)
        stat = os.stat(related_file)
        key = args_to_key(base, args + (related_file, stat.st_mtime, stat.st_size), {}, False, ())
    else:
        key = args_to_key(base, args, {}, False, ())

    result = cache.get(key)
    if result is None:
        result = func(*args)
        cache.set(key, result)

    return result






