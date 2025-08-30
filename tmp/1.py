import logging
import sys
from pathlib import Path

a = r"D:\BT下载\! --THE iDOLM@STER Music (Lossless)-- !\THE iDOLM@STER CINDERELLA GIRLS ANIMATION PROJECT\[2015.03.25] THE IDOLM@STER CINDERELLA GIRLS ANIMATION PROJECT 03 -LEGNE- 仇なす剣 光の旋律 (WAV+CUE)\「THE IDOLM@STER CINDERELLA GIRLS ANIMATION PROJECT 03 」『 -LEGNE- 仇なす剣 光の旋律』.cue"
b = r"D:\BT下载 克隆\! --THE iDOLM@STER Music (Lossless)-- !\THE iDOLM@STER CINDERELLA GIRLS ANIMATION PROJECT\[2015.03.25] THE IDOLM@STER CINDERELLA GIRLS ANIMATION PROJECT 03 -LEGNE- 仇なす剣 光の旋律 (WAV+CUE)\「THE IDOLM@STER CINDERELLA GIRLS ANIMATION PROJECT 03 」『 -LEGNE- 仇なす剣 光の旋律』.cue"

a, b = Path(a), Path(b)

print(a.exists(), len(str(a)), a.read_text("utf-8")[:50])
print(b.exists(), len(str(b)), b.read_text("utf-8")[:50])



