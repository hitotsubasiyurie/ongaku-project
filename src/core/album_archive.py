import os

from src.core.logger import logger
from src.external import rar_archive, rar_add, rar_list, rar_read, rar_rename, rar_stats


class AlbumArchive:

    def __init__(self, filepath: str) -> None:
        """
        :param filepath: 归档文件路径
        """
        self.path = filepath

    @staticmethod
    def from_album_directory(album_directory: str, **kwargs) -> "AlbumArchive":
        """
        :param album_directory: 专辑资源目录
        :param kwargs: AlbumArchive 实例化参数
        """
        archive = AlbumArchive(**kwargs)
        if os.path.exists(archive.path):
            logger.info(f"Remove existing archive. {archive.path}")
            os.unlink(archive.path)
        rar_archive(album_directory, archive.path)
        return archive

    def add(self, srcfiles: list[str], dstnames: list[str] = None) -> None:
        """
        添加文件。会覆盖已存在的目标文件。
        :param srcfile: 源文件路径
        :param dstname: 可选，目标文件名
        """
        rar_add(srcfiles, self.path)
        dstnames and rar_rename(self.path, list(map(os.path.basename, srcfiles)), dstnames)

    def list(self) -> list[str]:
        """
        列出文件列表。
        """
        return rar_list(self.path)

    def read(self, filename: str) -> bytes:
        """
        读取文件内容。
        :param filename: 文件名
        """
        return rar_read(self.path, filename)

    def stat(self, filenames: str) -> list[os.stat_result | None]:
        """
        统计文件属性。
        :param filename: 文件名
        """
        return rar_stats(self.path, filenames)


