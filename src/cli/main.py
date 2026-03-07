import os
import sys
from pathlib import Path

executable = Path(sys.argv[0])

# 若是源码运行 添加导包路径
if executable.suffix == ".py":
    sys.path[0] = str(executable.parent.parent.parent)
    os.chdir(executable.parent.parent.parent)
else:
    os.chdir(executable.parent)

from src.core.console import easy_cinput, cprint
from src.core.logger import logger

title2operation = {}

from src.operations.hardlink_copy import OPERATION_TITLE, hardlink_copy
title2operation[OPERATION_TITLE] = hardlink_copy

from src.operations.remove_file import OPERATION_TITLE, remove_file
title2operation[OPERATION_TITLE] = remove_file

from src.operations.recode import OPERATION_TITLE, recode
title2operation[OPERATION_TITLE] = recode

from src.operations.scrape_metadata import OPERATION_TITLE, scrape_metadata
title2operation[OPERATION_TITLE] = scrape_metadata

from src.operations.search_album_from_musicbrainz_database import OPERATION_TITLE, search_album_from_musicbrainz_database
title2operation[OPERATION_TITLE] = search_album_from_musicbrainz_database

from src.operations.merge_metadata import OPERATION_TITLE, merge_metadata
title2operation[OPERATION_TITLE] = merge_metadata

from src.operations.create_musicbrainz_database import OPERATION_TITLE, create_musicbrainz_database
title2operation[OPERATION_TITLE] = create_musicbrainz_database

from src.operations.shelve_audios import OPERATION_TITLE, shelve_audios
title2operation[OPERATION_TITLE] = shelve_audios

from src.operations.export_favourites import OPERATION_TITLE, export_favourites
title2operation[OPERATION_TITLE] = export_favourites

from src.operations.archive_albums import OPERATION_TITLE, archive_albums
title2operation[OPERATION_TITLE] = archive_albums


if __name__ == "__main__":

    titles, operations = list(title2operation.keys()), list(title2operation.values())
    while True:
        prompt = "\n".join(f"{i+1}. {m}" for i, m in enumerate(titles))
        number = easy_cinput(prompt, return_type=int)

        if not (0 <= number - 1 <= len(titles)):
            continue

        try:
            cprint(f"{'-'*8} {titles[number - 1]} {'-'*8}")
            func = operations[number - 1]
            if not func:
                break
            func()
            cprint("-"*32)
        except Exception as e:
            cprint(f"Error: {e}")
            logger.error("", exc_info=1)

