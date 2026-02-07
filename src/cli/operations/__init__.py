OPERATIONS = {}


from src.cli.operations.hardlink_copy import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.cli.operations.remove_files import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.cli.operations.recode import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.cli.operations.get_album_from_vgmdb import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.cli.operations.get_album_from_musicbrainz import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.cli.operations.search_album_from_musicbrainz_database import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.cli.operations.get_album_from_doujin_music_info import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.cli.operations.get_album_from_audiofiles import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.cli.operations.merge_metadata import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.cli.operations.create_musicbrainz_database import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.cli.operations.clean_audio_directory import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.cli.operations.archive_audio_files import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.cli.operations.export_favourite_songs import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.cli.operations.archive_resource import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from src.cli.operations.health_check import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

