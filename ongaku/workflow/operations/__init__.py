PLUGINS = {}


from ongaku.workflow.operations.hardlink_copy import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.workflow.operations.remove_files import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.workflow.operations.recode import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.workflow.operations.fetch_albums_metadata_from_vgmdb import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.workflow.operations.fetch_albums_metadata_from_musicbrainz import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.workflow.operations.fetch_albums_metadata_from_musicbrainz_database import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.workflow.operations.fetch_albums_metadata_from_doujin_music_info import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.workflow.operations.fetch_albums_metadata_from_audios import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.workflow.operations.merge_metadata import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.workflow.operations.create_musicbrainz_database import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.workflow.operations.clean_audio_directory import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.workflow.operations.archive_audio_files import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.workflow.operations.export_favourite_songs import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main


