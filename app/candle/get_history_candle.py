# 导入日志配置
import json
import logging.config
import time
from datetime import datetime


import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 锁定系统运行路径
project_path = Path(__file__).resolve().parent  # 此脚本的运行"绝对"路径
dotenv_path = os.path.join(project_path, '../')
sys.path.append(dotenv_path)

dotenv_path = os.path.join(project_path, '../../.env.dev')  # 指定.env.dev文件的路径
load_dotenv(dotenv_path)  # 载入环境变量
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# from utils.logging_config import Logging_dict

# logging.config.dictConfig(Logging_dict)
# LOGGING = logging.getLogger("app_01")



if __name__ == '__main__':



    from module.super_okx import GeniusTrader
    from utils.files import find_or_create_doc

    target_stock = "BTC-USDT"
    # target_stock = "LUNC-USDT"
    # target_stock = "ETH-USDT"
    # target_stock = "FLOKI-USDT"
    # target_stock = "OMI-USDT"
    # target_stock = "DOGE-USDT"
    # target_stock = "PEPE-USDT"
    # target_stock = "RACA-USDT"

    # target_stock = "JST-USDT"
    # target_stock = "ZRX-USDT"
    # target_stock = "ZIL-USDT"
    # target_stock = "ORDI-USDT"
    # target_stock = "BOME-USDT"  # 4H的时长不够
    # target_stock = "ARKM-USDT"  # 4H的时长不够
    # target_stock = "ZRO-USDT"  # 4H的时长不够
    # target_stock = "MEW-USDT"  # 4H的时长不够

    pre_day = None
    # pre_day = 1715587200000

    genius_trader = GeniusTrader()
    long_period_candle = []

# 注意错误
#         pre_day = total_candle[-1][0]
# IndexError: list index out of range

    max_day = 100
    max_day = 22
    for i in range(max_day):
        print(f"第: {i}次")
        # period = "1H"
        period = "4H"
        # period = "15m"
        total_candle = genius_trader.stock_candle(target_stock, after=pre_day, period=period)
        # total_candle.reverse()  # 由于时间，倒序
        pre_day = total_candle[-1][0]
        print(pre_day)
        print()
        long_period_candle.extend(total_candle)
        time.sleep(0.1)


    long_period_candle.reverse()
    # print(long_period_candle)
    # for i in long_period_candle:
    #     print(i)
    # print(len(long_period_candle))

    # total_path = os.path.join(BASE_DIR, f"./data/{target_stock}.json")
    # total_path = os.path.join(BASE_DIR, f"./data/{target_stock}-longtest.json")
    total_path = os.path.join(BASE_DIR, f"./data/{period}/{target_stock}.json")

    find_or_create_doc(total_path, 'json')
    json_data = json.dumps(long_period_candle)
    with open(total_path, 'w', encoding='utf-8') as f:
        f.write(json_data)

    with open(total_path, 'r') as file:
        loaded_data = json.load(file)
    # print(loaded_data)

    print(f"{target_stock} 写入完成")

