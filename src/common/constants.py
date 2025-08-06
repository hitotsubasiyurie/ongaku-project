import os

METADATA_PATH = os.getenv("ONGAKU_METADATA_PATH")
RESOURCE_PATH = os.getenv("ONGAKU_RESOURCE_PATH")
TMP_PATH = os.getenv("ONGAKU_TMP_PATH")

LOGFILE = os.path.join(TMP_PATH, "ongaku.log")

