from functools import cache
from typing import Literal, Union, Type

from src.toolkit.lang._en import Message as Message_en
from src.toolkit.lang._zh import Message as Message_zh
from src.toolkit.lang._ja import Message as Message_ja


MESSAGE: Union[Type[Message_en], Type[Message_zh], Type[Message_ja]] = Message_en

_LANG_MAP = {"en": Message_en, "zh": Message_zh, "ja": Message_ja}


@cache
def get_supported_language() -> list[str]:
    return list(_LANG_MAP.keys())


def set_language(lang: Literal["en", "zh", "ja"] = "en") -> None:
    global MESSAGE
    MESSAGE = _LANG_MAP.get(lang, Message_en)

