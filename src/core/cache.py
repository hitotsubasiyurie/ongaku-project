import os
from typing import Callable, Any

from diskcache import Cache
from diskcache.core import full_name, args_to_key

from src.core.settings import settings
from src.core.logger import logger


cache = Cache(os.path.join(settings.temp_directory, "cache"), size_limit=50*1024*1024)

request_cache = Cache(os.path.join(settings.temp_directory, "request_cache"), size_limit=100*1024*1024)


def with_cache(func: Callable, *args, related_file: str = "") -> Any:
    """
    :param related_file: 关联的文件
    """
    # 实现参考 diskcache.core.memoize
    base = (full_name(func),)
    if related_file:
        stat = os.stat(related_file)
        key = args_to_key(base, args + (related_file, stat.st_mtime, stat.st_size), {}, False, ())
    else:
        key = args_to_key(base, args, {}, False, ())

    logger.info(key)

    result = cache.get(key)
    if result is None:
        result = func(*args)
        cache.set(key, result)

    return result






