

import os

path = r"D:\ongaku-resource\AnimeComicGame\アイドルマスター [偶像大师] [THE IDOLM@STER]\[LABX-38090, LABX-38091, LABX-38092, LABX-38093, LABX-38094] [2014-12-24] THE IDOLM@STER MILLION LIVE! 1stLIVE HAPPY☆PERFORM@NCE!! Blu-ray ＂COMPLETE THE@TER＂ [Limited Edition] Vocal, Live Event [2]"

print(os.path.isdir(path))

import subprocess

# 能运行
subprocess.run(r"E:\tool\Notepad4\Notepad4.exe")

# 不能运行
subprocess.run(r"E:\tool\Notepad4\Notepad4.exe", cwd=path)




