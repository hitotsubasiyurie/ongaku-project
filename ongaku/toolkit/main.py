import os

from ongaku.logger import logger, set_logger_output, lprint
from ongaku.settings import global_settings
from ongaku.toolkit.message import MESSAGE, set_language, get_supported_languages
from ongaku.toolkit.actions import (hardlink_copy, create_musicbrainz_database, fetch_albums_metadata_from_vgmdb, 
    fetch_albums_metadata_from_musicbrainz_database, match_resource_and_metadata, merge_metadata_files, recode,
    remove_files)
from ongaku.toolkit.toolkit_utils import loop_for_actions


def ask_for_lang() -> str:
    langs = get_supported_languages()
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

    if global_settings.language not in get_supported_languages():
        global_settings.language = ask_for_lang()
    
    set_language(global_settings.language)

    if not global_settings.temp_directory:
        global_settings.temp_directory = ask_for_temp_dir()

    set_logger_output(global_settings.temp_directory)

    message2action = {
        MESSAGE.AUP6NZT5: hardlink_copy,
        MESSAGE.WFSEKVW9: remove_files,
        MESSAGE.GB5JO189: recode,
        MESSAGE.GBT3D4H8: fetch_albums_metadata_from_vgmdb,
        MESSAGE.VKTS4CY7: fetch_albums_metadata_from_musicbrainz_database,
        MESSAGE.ZJFV9Z1X: merge_metadata_files,
        MESSAGE.B2BHBP2H: match_resource_and_metadata,
        MESSAGE.ER5LSXY9: create_musicbrainz_database,
        MESSAGE.CLZWFPBZ: None
    }

    loop_for_actions(message2action)


if __name__ == "__main__":
    main()


