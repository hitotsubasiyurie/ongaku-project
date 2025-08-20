import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.common.logger import logger
from src.common.constants import METADATA_PATH, TMP_PATH, RESOURCE_PATH
from src.common.utils import strings_assignment
from src.common.exception import OngakuException
from src.metadata_source.vgmdb_api import VGMdbAPI
from src.ongaku_library.ongaku_library import dump_album_model, album_filename, OngakuScanner


if __name__ == "__main__":

    metadata_dir = input(f"Please input metadata directory ({METADATA_PATH}): ").strip("'\"") or METADATA_PATH
    resource_dir = input(f"Please input resource directory ({RESOURCE_PATH}): ").strip("'\"") or RESOURCE_PATH

    if not metadata_dir or not resource_dir:
        sys.exit(0)

    ongaku_library = OngakuScanner(metadata_dir, resource_dir)

    for mdf, dst_mdf, res_dir, dst_dir in zip(ongaku_library.get_album_metadata_files(), ongaku_library.get_album_dst_metadata_files(), 
                                              ongaku_library.get_album_resource_dirs(), ongaku_library.get_album_dst_resource_dirs()):
        
        old_name = Path(mdf).stem
        new_name = Path(dst_mdf).stem

        # 移动 元数据文件
        if old_name != new_name:
            os.rename(mdf, dst_mdf)
            logger.info(f"{mdf} -> {dst_mdf}")

        # 无资源 跳过
        if not res_dir:
            continue

        dst_dir = Path(dst_dir).parent / new_name

        if res_dir == dst_dir:
            continue

        dst_dir.parent.mkdir(exist_ok=True, parents=True)
        os.rename(res_dir, dst_dir)
        logger.info(f"{res_dir} -> {dst_dir}")

    # 删除空目录
    [d.rmdir() for d in Path(resource_dir).rglob("*") if d.is_dir() and not os.listdir(d)]












