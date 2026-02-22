import os
import shutil
from pathlib import Path

from src.core.i18n import MESSAGE
from src.core.logger import lprint
from src.core.settings import settings
from src.core.kanban import Kanban
from src.external import rar_archive, rar_add

OPERATION_NAME = MESSAGE.WF_20251221_202001


# 主函数

def archive_resource() -> None:
    kanban = Kanban(settings.metadata_directory, settings.resource_directory)

    total = sum(1 for tk in kanban.theme_kanbans for ak in tk.album_kanbans if os.path.isdir(ak.album_dir))
    current = 0

    for tk in kanban.theme_kanbans:

        for ak in tk.album_kanbans:

            # 跳过 专辑目录 不存在
            if not os.path.isdir(ak.album_dir):
                continue

            current += 1

            # 清理 空的 专辑目录
            if not os.listdir(ak.album_dir):
                os.rmdir(ak.album_dir)
                continue

            if os.path.isfile(ak.album_archive):
                rar_add(ak.album_archive, list(Path(ak.album_dir).glob("*")))
            else:
                rar_archive(ak.album_archive, ak.album_dir)
            shutil.rmtree(ak.album_dir)
            lprint(MESSAGE.WF_20251221_202003.format(current, total, ak.album_dir, ak.album_archive))

        # 清理 空的 主题目录
        if os.path.isdir(tk.theme_resource_dir) and not os.listdir(tk.theme_resource_dir):
            os.rmdir(tk.theme_resource_dir)



