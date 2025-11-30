PLUGINS = {}


from ongaku.toolkit.operations.hardlink_copy import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.toolkit.operations.remove_files import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.toolkit.operations.recode import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.toolkit.operations.fetch_albums_metadata_from_vgmdb import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.toolkit.operations.fetch_albums_metadata_from_musicbrainz import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.toolkit.operations.fetch_albums_metadata_from_musicbrainz_database import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.toolkit.operations.fetch_albums_metadata_from_doujin_music_info import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.toolkit.operations.fetch_albums_metadata_from_audios import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.toolkit.operations.merge_metadata import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.toolkit.operations.create_musicbrainz_database import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.toolkit.operations.clean_audio_directory import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.toolkit.operations.archive_audio_files import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.toolkit.operations.export_favourite_songs import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main


