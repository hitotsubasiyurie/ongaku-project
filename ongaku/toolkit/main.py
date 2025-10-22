import os
import sys
import uuid
import importlib.util
from pathlib import Path

executable = Path(sys.argv[0])
# 指定运行目录 当前父目录
os.chdir(executable.parent)

# 若是源码运行 添加导包路径
if executable.suffix == ".py":
    sys.path[0] = str(executable.parent.parent.parent)

from ongaku.core.logger import set_logger_output
from ongaku.core.settings import global_settings
from ongaku.toolkit.toolkit_utils import loop_for_actions


PLUGIN_DIR = Path("./plugin")


def main():

    # 初始化 目录
    for p in [global_settings.temp_directory, global_settings.metadata_directory, global_settings.resource_directory]:
        os.makedirs(p, exist_ok=True)
    
    set_logger_output(global_settings.temp_directory)

    message2action = {}

    # 仅扫描 表层 py 文件
    for file in PLUGIN_DIR.glob("*.py"):
        spec = importlib.util.spec_from_file_location(f"plugin_{uuid.uuid4().hex}", file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        plugin_main = getattr(module, "main", None)
        plugin_name = getattr(module, "PLUGIN_NAME", None)

        if callable(plugin_main):
            message2action[plugin_name or file.name] = plugin_main
    
    loop_for_actions(message2action)


if __name__ == "__main__":
    main()


