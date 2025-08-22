import time
from functools import wraps
from pathlib import Path
from threading import Lock
from typing import Callable, Generator, Mapping, Any
from difflib import SequenceMatcher

import numpy
from scipy.optimize import linear_sum_assignment

from src.common.logger import logger


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


def strings_assignment(strings_a: list[str], strings_b: list[str]) -> tuple[float, list[int], list[int]]:
    """
    字符串最大相似度分配。
        b1 b2 b3 ... bm
    a1
    a2
    a3
    ...
    an
    :param strings_a: 字符串列表 [a1, a2, a3, ..., an]
    :param strings_b: 字符串列表 [b1, b2, b3, ..., bm]
    """
    sim_matrix = [[SequenceMatcher(None, sa, sb).ratio() for sb in strings_b] 
                   for sa in strings_a]
    sim_matrix = numpy.asarray(sim_matrix)
    row_ind, col_ind = linear_sum_assignment(sim_matrix, maximize=True)
    aver_similarity = sim_matrix[row_ind, col_ind].sum() / len(row_ind)
    return aver_similarity, row_ind, col_ind


def dump_toml(obj: Mapping[str, Any], file: str = None) -> str:

    from tomli_w._writer import Context, format_literal, ARRAY_TYPES

    def custom_format_inline_array(obj: tuple | list, ctx: Context, nest_level: int) -> str:
        if not obj:
            return "[]"
        item_indent = ctx.indent_str * (1 + nest_level)
        closing_bracket_indent = ctx.indent_str * nest_level
        # 扁平列表
        if not any(isinstance(item, ARRAY_TYPES) for item in obj):
            return "[" + ", ".join(format_literal(item, ctx, nest_level=nest_level + 1) for item in obj) + f"]"
        return (
            "[\n"
            + ",\n".join(
                item_indent + format_literal(item, ctx, nest_level=nest_level + 1)
                for item in obj
            )
            + f",\n{closing_bracket_indent}]"
        )
    
    import tomli_w._writer
    tomli_w._writer.format_inline_array = custom_format_inline_array


    text = tomli_w.dumps(obj)
    file and Path(file).write_text(text, encoding="utf-8")
    return text
