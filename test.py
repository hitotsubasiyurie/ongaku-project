
import json
from datetime import datetime


ss = datetime.now().strftime("%d/%m/%Y, %H:%M:%S")

d = {1: ss}

print(json.dumps(d))









