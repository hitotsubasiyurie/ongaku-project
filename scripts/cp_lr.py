"""
模拟 cp -lR 的行为
"""

import sys
from pathlib import Path

src_given = Path(input("请输入绝对源路径：").strip("'\""))
dst_given = Path(input("请输入绝对目标路径：").strip("'\""))

if src_given.is_file():
    dst_given.hardlink_to(src_given)
    sys.exit()

dst_given.mkdir(parents=True, exist_ok=True)

src_files = list(src_given.rglob("*"))
dst_files = [dst_given / src.relative_to(src_given) for src in src_files]

dst_given.mkdir(parents=True, exist_ok=True)
[dst.hardlink_to(src) if src.is_file() else dst.mkdir() for src, dst in zip(src_files, dst_files)]


