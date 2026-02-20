



import os
from pathlib import Path


directory = r"F:\ongaku-archive\AnimeComicGame\Aチャンネル [A频道] [A-Channel]"


print(list(map(os.path.abspath, Path(directory).rglob("*"))))

print(list(os.path.join(directory, f.name) for f in Path(directory).rglob("*")))

print()


