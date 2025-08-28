import os
import sys
import json
from pathlib import Path

from src.logger import set_logger_output, lprint
from src.toolkit.utils import easy_linput
from src.toolkit.lang.message import MESSAGE, set_language, get_supported_language


SETTINGS_FILE = Path(sys.argv[0]).parent / "settings.json"
LANGUAGE = "language"
TEMP_DIRECTORY = "temp_directory"
METADATA_DIRECTORY = "metadata_directory"
RESOURCE_DIRECTORY = "resource_directory"


def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    return {}


def save_settings(settings: dict) -> None:
    SETTINGS_FILE.write_text(json.dumps(settings, ensure_ascii=False, indent=4), encoding="utf-8")


def ask_for_lang() -> str:
    langs = get_supported_language()
    langs_str = ", ".join()
    while True:
        lang = input(f"Please choose the language [{langs_str}]:").strip()
        if lang in langs:
            return lang


def ask_for_temp_dir() -> str:
    while True:
        ongaku_tmp = input(MESSAGE.S9G87W7).strip("'\"")
        if not ongaku_tmp or not os.path.isdir(ongaku_tmp): 
            continue
        return ongaku_tmp


def main():
    settings = load_settings()

    if settings.get(LANGUAGE) not in get_supported_language():
        settings[LANGUAGE] = ask_for_lang()
    
    set_language(settings[LANGUAGE])

    if TEMP_DIRECTORY not in settings:
        settings[TEMP_DIRECTORY] = ask_for_temp_dir()

    set_logger_output(settings[TEMP_DIRECTORY])

    while True:
        lprint(MESSAGE.S0DMGK4)
        action = easy_linput(return_type=int)



if __name__ == "__main__":
    main()
    













