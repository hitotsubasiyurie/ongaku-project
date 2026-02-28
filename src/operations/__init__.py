OPERATIONS = {}


from src.operations.hardlink_copy import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.operations.remove_files import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.operations.recode import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.operations.get_album_from_vgmdb import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.operations.get_album_from_musicbrainz import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.operations.search_album_from_musicbrainz_database import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.operations.get_album_from_doujin_music_info import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.operations.get_album_from_audiofiles import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.operations.merge_metadata import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.operations.create_musicbrainz_database import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.operations.clean_audio_directory import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.operations.archive_audio_files import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.operations.export_favourite_songs import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.operations.archive_resource import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.operations.health_check import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

