PLUGINS = {}


from ongaku.toolkit.plugins.hardlink_copy import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.toolkit.plugins.remove_files import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.toolkit.plugins.recode import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.toolkit.plugins.fetch_albums_metadata_from_vgmdb import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.toolkit.plugins.fetch_albums_metadata_from_musicbrainz import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.toolkit.plugins.fetch_albums_metadata_from_musicbrainz_database import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.toolkit.plugins.merge_metadata import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.toolkit.plugins.create_musicbrainz_database import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.toolkit.plugins.clean_audio_directory import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.toolkit.plugins.archive_audio_files import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main

from ongaku.toolkit.plugins.export_favourite_songs import PLUGIN_NAME, main
PLUGINS[PLUGIN_NAME] = main
