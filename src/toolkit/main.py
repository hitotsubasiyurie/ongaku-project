import os
import sys
import json
from pathlib import Path

from src.logger import set_output, lprint

settings = {}

settings_file = Path(sys.argv[0]).parent / "settings.json"

if settings_file.exists():
    settings = json.loads(settings_file.read_text(encoding="utf-8"))

if "ONGAKU_TMP" not in settings:
    ongaku_tmp = input("Please input a existing directory to save temp files: ").strip("'\"")
    if not ongaku_tmp or not os.path.isdir(ongaku_tmp): 
        sys.exit(0)
    settings["ONGAKU_TMP"] = ongaku_tmp

if "LANGUAGE" not in settings:
    print("Please choose the language:")
    print("zh: 简体中文")
    print("en: English")
    print("ja: 日本语")
    lang = input().strip()
    if lang not in ["zh", "en", "ja"]:
        sys.exit(0)
    settings["LANGUAGE"] = lang

settings_file.write_text(json.dumps(settings, ensure_ascii=False, indent=4))

if lang == "zh":
    from src.toolkit.lang.zh import *
elif lang == "en":
    from src.toolkit.lang.en import *
elif lang == "ja":
    from src.toolkit.lang.ja import *


if __name__ == "__main__":

    lprint(MESSAGE_A9FM6)
















