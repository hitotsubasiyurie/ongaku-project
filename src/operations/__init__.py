OPERATIONS = {}


from src.operations.hardlink_copy import OPERATION_NAME, hardlink_copy
OPERATIONS[OPERATION_NAME] = hardlink_copy

from src.operations.remove_file import OPERATION_NAME, remove_file
OPERATIONS[OPERATION_NAME] = remove_file

from src.operations.recode import OPERATION_NAME, recode
OPERATIONS[OPERATION_NAME] = recode

from src.operations.get_album_from_vgmdb import OPERATION_NAME, get_album_from_vgmdb
OPERATIONS[OPERATION_NAME] = get_album_from_vgmdb

from src.operations.get_album_from_musicbrainz import OPERATION_NAME, get_album_from_musicbrainz
OPERATIONS[OPERATION_NAME] = get_album_from_musicbrainz

from src.operations.search_album_from_musicbrainz_database import OPERATION_NAME, search_album_from_musicbrainz_database
OPERATIONS[OPERATION_NAME] = search_album_from_musicbrainz_database

from src.operations.get_album_from_doujinmusicinfo import OPERATION_NAME, get_album_from_doujinmusicinfo
OPERATIONS[OPERATION_NAME] = get_album_from_doujinmusicinfo

from src.operations.merge_metadata import OPERATION_NAME, merge_metadata
OPERATIONS[OPERATION_NAME] = merge_metadata

from src.operations.create_musicbrainz_database import OPERATION_NAME, create_musicbrainz_database
OPERATIONS[OPERATION_NAME] = create_musicbrainz_database

from src.operations.shelve_audios import OPERATION_NAME, shelve_audios
OPERATIONS[OPERATION_NAME] = shelve_audios

from src.operations.export_favourites import OPERATION_NAME, export_favourites
OPERATIONS[OPERATION_NAME] = export_favourites

from src.operations.archive_albums import OPERATION_NAME, archive_albums
OPERATIONS[OPERATION_NAME] = archive_albums

