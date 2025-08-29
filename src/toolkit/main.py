import os
import sys
import json
from pathlib import Path

from src.logger import set_logger_output, lprint
from src.global_settings import global_settings
from src.toolkit.toolkit_utils import easy_linput
from src.toolkit.message import MESSAGE, set_language, get_supported_language
from src.toolkit.actions import hardlink_copy, create_musicbrainz_database


def ask_for_lang() -> str:
    langs = get_supported_language()
    langs_str = ", ".join(langs)
    while True:
        lang = input(f"Please choose a language [{langs_str}]:\n").strip()
        if lang in langs:
            return lang


def ask_for_temp_dir() -> str:
    while True:
        ongaku_tmp = input(MESSAGE.FMJEKLYK).strip("'\"")
        if not ongaku_tmp or not os.path.isdir(ongaku_tmp): 
            continue
        return ongaku_tmp


def main():

    if global_settings.language not in get_supported_language():
        global_settings.language = ask_for_lang()
    
    set_language(global_settings.language)

    if not global_settings.temp_directory:
        global_settings.temp_directory = ask_for_temp_dir()

    set_logger_output(global_settings.temp_directory)

    while True:
        # lprint(MESSAGE.S0DMGK4)
        action = easy_linput(return_type=int)

        if action == 1:
            hardlink_copy()



if __name__ == "__main__":
    main()
    


# 1. 管理员权限










