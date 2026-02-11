import os
import shutil

from src.core.kanban import Kanban
from src.core.logger import lprint
from src.core.settings import settings
from src.core.i18n import MESSAGE
from src.cli.common import easy_linput
from src.external import rar_archive


OPERATION_NAME = MESSAGE.WF_20251221_202001


# 主函数

def main() -> None:
    kanban = Kanban(settings.metadata_directory, settings.resource_directory, settings.archive_directory)

    total = sum(1 for tk in kanban.theme_kanbans for ak in tk.album_kanbans if os.path.isdir(ak.album_dir))
    current = 0

    for theme_kanban in kanban.theme_kanbans:

        for album_kanban in theme_kanban.album_kanbans:

            # 跳过 专辑目录 不存在
            if not os.path.isdir(album_kanban.album_dir):
                continue

            current += 1

            # 清理 空的 专辑目录
            if not os.listdir(album_kanban.album_dir):
                os.rmdir(album_kanban.album_dir)
                continue

            # 存在归档文件时
            while True:
                if os.path.isfile(album_kanban.album_archive):
                    easy_linput(MESSAGE.WF_20251221_202002.format(album_kanban.album_archive), default="")
                    continue
                break

            os.makedirs(os.path.dirname(album_kanban.album_archive), exist_ok=True)
            rar_archive(album_kanban.album_archive, album_kanban.album_dir)
            shutil.rmtree(album_kanban.album_dir)
            lprint(MESSAGE.WF_20251221_202003.format(current, total, album_kanban.album_dir, album_kanban.album_archive))

        # 清理 空的 主题目录
        if os.path.isdir(theme_kanban.theme_resource_dir) and not os.listdir(theme_kanban.theme_resource_dir):
            os.rmdir(theme_kanban.theme_resource_dir)





