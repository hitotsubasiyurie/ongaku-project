import sys
import csv
import time
import json
import pickle
from pathlib import Path
from collections import defaultdict

import orjson



album_db = Path(r"D:\移动云盘同步盘\20250802-001001.album")
csv_file = Path(r"D:\1.csv")


rf = album_db.open("r", encoding="utf-8")
wf = csv_file.open("w", encoding="utf-8", newline="")

fieldnames = ["release_id", "catalognumber", "date", "album", "tracks", "themes", "links"]
writer = csv.DictWriter(wf, fieldnames=fieldnames, quoting=csv.QUOTE_STRINGS)
writer.writeheader()

for album in map(orjson.loads, rf):
    album["release_id"] = album["links"][0].split("/")[-1]
    album["catalognumber"] = "" 
    album["tracks"] = json.dumps(album["tracks"], ensure_ascii=False)
    album["themes"] = set(album["themes"]) if album["themes"] else {}
    album["links"] = set(album["links"]) if album["links"] else {}
    writer.writerow(album)

