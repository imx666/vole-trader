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

    with open('market_monitor.json', 'r') as file:
        target_stock_li = json.load(file)


    genius_trader = GeniusTrader()



    max_day = 100
    # max_day = 22

    for target_stock in target_stock_li:
        try:
            pre_day = None
            long_period_candle = []
            for i in range(max_day):
                print(f"第: {i}次")
                # period = "1H"
                # period = "4H"
                period = "15m"
                total_candle = genius_trader.stock_candle(target_stock, after=pre_day, period=period)
                # total_candle.reverse()  # 由于时间，倒序
                pre_day = total_candle[-1][0]
                print(pre_day)
                print()
                long_period_candle.extend(total_candle)
                time.sleep(0.1)
            long_period_candle.reverse()
            total_path = os.path.join(BASE_DIR, f"./data/{period}/{target_stock}.json")

            find_or_create_doc(total_path, 'json')
            json_data = json.dumps(long_period_candle)
            with open(total_path, 'w', encoding='utf-8') as f:
                f.write(json_data)

            print(f"{target_stock} 写入完成")
        except Exception as e:
            print("error",e)
            continue





