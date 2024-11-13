from datetime import datetime
import time

# 获取当前时间戳
timestamp = int(time.time())
print("当前时间戳:", timestamp)

current_time = datetime.now().strftime("%Yy%mm%dd%Hh%Mm%Ss")

print(current_time)
