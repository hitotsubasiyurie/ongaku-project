"""
与项目无关的，外部工具函数
"""

import mimetypes
import time
import uuid
from functools import wraps
from pathlib import Path
from threading import Lock
from typing import Callable, Mapping, Any

from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, APIC, PictureType
from mutagen.mp3 import EasyMP3, MP3


def retry(retries: int = 3, delay: int | float = 5) -> Callable:
    """
    重试装饰器。

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
    函数调用频率限制装饰器。

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
    3. 限制 250 字符文件名
    
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


def dump_toml(obj: Mapping[str, Any], file: str = None) -> str:
    """
    1. 扁平列表不换行缩进
    
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
    old = tomli_w._writer.format_inline_array
    tomli_w._writer.format_inline_array = custom_format_inline_array
    try:
        text = tomli_w.dumps(obj)
    finally:
        tomli_w._writer.format_inline_array = old

    file and Path(file).write_text(text, encoding="utf-8")
    return text


def read_audio_cover(audio: str) -> bytes:
    """
    读取音频封面。

    :param audio: 音频文件，格式 [".mp3", ".flac"]
    """
    audio = Path(audio)
    if audio.suffix.lower() == ".flac":
        flac = FLAC(audio)
        # 无封面
        if not flac.pictures:
            return b""
        return flac.pictures[0].data

    elif audio.suffix.lower() == ".mp3":
        mp3 = MP3(audio, ID3=ID3)
        # 无封面
        apic_tag = next((t for t in mp3.tags.values() if isinstance(t, APIC)), None)
        if not apic_tag:
            return b""
        return apic_tag.data


def read_audio_tags(audio: str, standard: bool = True) -> dict[str, str]:
    """
    读取音频标准元数据标签。
    
    标准化标签：
    1. 包含键 ["catalognumber", "date", "album", "tracknumber", "title", "artist"]
    2. 值为字符串，以 // 为多值连接符

    :param audio: 音频文件，格式 [".mp3", ".flac"]
    :param standard: 是否返回标准化标签
    """
    audio = Path(audio)
    if audio.suffix.lower() == ".flac":
        tags = FLAC(audio).tags
    elif audio.suffix.lower() == ".mp3":
        tags = EasyMP3(audio).tags
    if tags is None:
        tags = {}
    if not standard:
        return dict(tags)
    standard_tags = {k: "//".join(tags.get(k, [])) 
                     for k in ["catalognumber", "date", "album", "tracknumber", "title", "artist"]}
    return standard_tags


def write_audio_tags(audio: str, 
                     cover: str = "",
                     catalognumber: str = "", date: str = "", album: str = "",
                     tracknumber: str = "", title: str = "", artist: str = "") -> None:
    """
    写入音频元数据标签。仅更新传入的非空值。

    :param audio: 音频文件，格式 [".mp3", ".flac"]
    """
    audio = Path(audio)

    tag_fields = ["catalognumber", "date", "album", "tracknumber", "title", "artist"]
    tags = {k: str(locals().get(k)) for k in tag_fields if locals().get(k)}

    if audio.suffix.lower() == ".flac":
        flac = FLAC(audio)
        flac.update(tags)

        if cover:
            pic = Picture()
            pic.type = PictureType.COVER_FRONT
            pic.mime = mimetypes.guess_type(cover)[0] or "image/jpeg"
            pic.data = Path(cover).read_bytes()
            flac.clear_pictures()
            flac.add_picture(pic)
        
        flac.save()

    elif audio.suffix.lower() == ".mp3":
        mp3 = EasyMP3(audio)
        mp3.update(tags)
        mp3.save()

        if cover:
            id3 = ID3(audio)
            id3.delall("APIC")
            mime = mimetypes.guess_type(cover)[0] or "image/jpeg"
            id3.add(APIC(encoding=3, desc="Cover", mime=mime, type=PictureType.COVER_FRONT, 
                         data=Path(cover).read_bytes()))
            id3.save(audio)


