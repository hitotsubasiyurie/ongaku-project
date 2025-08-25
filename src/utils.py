"""
外部工具函数
"""

import os
import time
import uuid
from functools import wraps
from pathlib import Path
from threading import Lock
from typing import Callable, Generator, Mapping, Any
from difflib import SequenceMatcher

import numpy
from scipy.optimize import linear_sum_assignment
from mutagen.flac import FLAC
from mutagen.mp3 import EasyMP3
import tomli_w


def retry(retries: int = 3, delay: int | float = 5) -> Callable:
    """
    重试装饰器。\n
    :param retries: 重试次数
    :param delay: 重试间隔秒
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while attempt < retries:
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
    """
    函数调用频率限制装饰器。\n
    :param interval: 调用间隔秒
    """

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
    1. 用全角符号替换路径中的非法符号
    2. 去除路径结尾空格
    3. 限制 250 字符文件名\n
    :param name: 文件名，如 1.txt
    """
    name = str(name)
    for i, j in zip(r'\/:*?"<>|', "＼／：＊？＂＜＞｜"):
        name = name.replace(i, j)
        name = name.rstrip()
    if len(name) > 255:
        ext = Path(name).suffix
        uid = str(uuid.uuid3(uuid.NAMESPACE_X500, name))
        name = name[:250-36-len(ext)] + uid + ext
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
    """
    1. 扁平列表不换行缩进\n
    :param obj: 字典
    :param file: 可选，保存的文件路径
    :return text: 
    """

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


def read_audio_tags(audio: str, standard: bool = True) -> dict[str, Any]:
    """
    读取音频标准元数据标签。\n
    :param audio: 音频文件，格式 [".mp3", ".flac"]
    :param standard: 是否返回标准化标签

    标准化标签：
    1. 包含键 ["catalognumber", "date", "album", "tracknumber", "title", "artist"]
    2. 值为字符串，以 // 为多值连接符
    """
    audio = Path(audio)
    if audio.suffix == ".flac":
        tags = FLAC(audio).tags
    elif audio.suffix == ".mp3":
        tags = EasyMP3(audio).tags
    if not standard:
        return dict(tags)
    standard_tags = {k: "//".join(tags.get(k, [])) 
                     for k in ["catalognumber", "date", "album", "tracknumber", "title", "artist"]}
    return standard_tags

