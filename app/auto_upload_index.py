import time
import schedule
import logging.config
import json
import os
import redis
from pathlib import Path

# 导入日志配置
import logging.config
from datetime import datetime

from utils.logging_config import Logging_dict

logging.config.dictConfig(Logging_dict)
LOGGING = logging.getLogger("auto_upload_index")


from module.super_okx import GeniusTrader
from utils.url_center import redis_url
from module.common_index import get_DochianChannel, get_ATR

genius_trader = GeniusTrader()

BASE_DIR = Path(__file__).resolve().parent.parent
total_path = os.path.join(BASE_DIR, f"./target_stocks.json")
with open(total_path, 'r') as file:
    target_stock_li = json.load(file)


# target_stock_li = [
#     "BTC-USDT",
#     "ETH-USDT",
#     "DOGE-USDT",
#     "XRP-USDT",
#     "LUNC-USDT",
#     "FLOKI-USDT",
#     "OMI-USDT",
#     "PEPE-USDT",
# ]

def update_job():
    for target_stock in target_stock_li:
        # 尝试爬取
        for i in range(1, 5):
            if i == 4:
                LOGGING.error(f"--彻底失败\n")
                continue
            try:
                total_candle = genius_trader.stock_candle(target_stock, period="4H")
                # print(total_candle)
                PERIOD = 3
                history_max_price, history_min_price = get_DochianChannel(total_candle, PERIOD)
                ATR = get_ATR(total_candle, PERIOD)

                redis_okx = redis.Redis.from_url(redis_url)
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                redis_okx.hset(f"common_index:{target_stock}", 'update_time', current_time)
                redis_okx.hset(f"common_index:{target_stock}",
                               mapping={'history_max_price': history_max_price, 'history_min_price': history_min_price,
                                        'ATR': ATR})

                LOGGING.info(f"target_stock:{target_stock}")
                LOGGING.info(f"history_max_price:{history_max_price}")
                LOGGING.info(f"history_min_price:{history_min_price}")
                LOGGING.info(f"ATR:{ATR}\n")
                break
            except Exception as e:
                LOGGING.warning(f"爬取失败--第{i}次:{e}")
                time.sleep(5)


if __name__ == "__main__":

    update_job()

    # 每天的特定小时执行任务
    hours_to_run = [0, 4, 8, 12, 16, 20]  # 23点是为了清空当天的尾巴信息
    LOGGING.info(f"定时任务启动,在每天的{hours_to_run}点执行任务\n")
    for hour in hours_to_run:
        schedule.every().day.at(f"{hour:02}:01").do(update_job)

    # 执行定时任务的主循环
    while True:
        schedule.run_pending()
        time.sleep(1)
