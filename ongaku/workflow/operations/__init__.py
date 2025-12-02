OPERATIONS = {}


from ongaku.workflow.operations.hardlink_copy import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from ongaku.workflow.operations.remove_files import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from ongaku.workflow.operations.recode import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from ongaku.workflow.operations.fetch_albums_metadata_from_vgmdb import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from ongaku.workflow.operations.fetch_albums_metadata_from_musicbrainz import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from ongaku.workflow.operations.fetch_albums_metadata_from_musicbrainz_database import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from ongaku.workflow.operations.fetch_albums_metadata_from_doujin_music_info import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from ongaku.workflow.operations.fetch_albums_metadata_from_audios import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from ongaku.workflow.operations.merge_metadata import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from ongaku.workflow.operations.create_musicbrainz_database import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from ongaku.workflow.operations.clean_audio_directory import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from ongaku.workflow.operations.archive_audio_files import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main

from ongaku.workflow.operations.export_favourite_songs import OPERATION_NAME, main
OPERATIONS[OPERATION_NAME] = main


