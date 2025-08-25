import os
import subprocess
import signal
from pathlib import Path
from typing import Generator

import os
import subprocess
import io
from typing import Generator



date = "201?-04-01"
# date = "2011-??-04"
# date = "1042-01-1?"


date = "-".join(date.split("?")[0].split("-")[:-1])

print([date])

