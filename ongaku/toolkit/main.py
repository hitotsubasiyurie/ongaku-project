import os
import sys
from pathlib import Path

executable = Path(sys.argv[0])

if executable.suffix == ".py":
    sys.path[0] = str(executable.parent.parent.parent)
    os.chdir(executable.parent.parent.parent)
else:
    os.chdir(executable.parent)

from ongaku.core.logger import set_logger_output, set_logger_level
from ongaku.core.settings import global_settings
from ongaku.toolkit.utils import loop_for_actions
from ongaku.toolkit.operations import PLUGINS


PLUGIN_DIR = Path("./plugin")


def main():

    # 初始化 目录
    for p in [global_settings.temp_directory, global_settings.metadata_directory, global_settings.resource_directory]:
        os.makedirs(p, exist_ok=True)
    
    set_logger_output(global_settings.temp_directory)
    set_logger_level(global_settings.log_level)

    loop_for_actions(PLUGINS)


if __name__ == "__main__":
    main()

