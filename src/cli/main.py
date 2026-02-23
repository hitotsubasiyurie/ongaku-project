import os
import sys
from pathlib import Path

executable = Path(sys.argv[0])

if executable.suffix == ".py":
    sys.path[0] = str(executable.parent.parent.parent)
    os.chdir(executable.parent.parent.parent)
else:
    os.chdir(executable.parent)

from src.core.settings import g_settings
from src.cli.common import loop_for_actions
from src.cli.operations import OPERATIONS


def main():

    # 初始化 目录
    for p in [g_settings.metadata_directory, g_settings.resource_directory]:
        os.makedirs(p, exist_ok=True)
    
    loop_for_actions(OPERATIONS)


if __name__ == "__main__":
    main()

