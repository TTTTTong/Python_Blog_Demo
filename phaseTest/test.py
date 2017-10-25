from datetime import datetime
import time
print(time.time())
dt = datetime.fromtimestamp(time.time())
print(dt.hour)
