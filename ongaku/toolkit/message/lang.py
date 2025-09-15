from typing import Union, Type, TYPE_CHECKING

from ongaku.toolkit.message._en import Message as Message_en
from ongaku.toolkit.message._zh import Message as Message_zh
from ongaku.toolkit.message._ja import Message as Message_ja


_LANG_MAP = {"en": Message_en, "zh": Message_zh, "ja": Message_ja}

_current_message = Message_en


def get_supported_languages() -> list[str]:
    return list(_LANG_MAP.keys())


def set_language(lang: str = "en") -> None:
    global _current_message
    _current_message = _LANG_MAP.get(lang, Message_en)


if TYPE_CHECKING:
    MESSAGE: Union[Type[Message_en], Type[Message_zh], Type[Message_ja]]
else:
    class _MessageProxy:
        def __getattr__(self, name: str):
            return getattr(_current_message, name)

    MESSAGE = _MessageProxy()
