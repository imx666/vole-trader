# 导入日志配置
import json
import logging.config
from datetime import datetime

from utils.logging_config import Logging_dict

logging.config.dictConfig(Logging_dict)
LOGGING = logging.getLogger("app_01")



if __name__ == '__main__':

    import os
    from pathlib import Path
    from dotenv import load_dotenv

    project_path = Path(__file__).resolve().parent  # 此脚本的运行"绝对"路径
    dotenv_path = os.path.join(project_path, '../.env.dev')  # 指定.env.dev文件的路径
    load_dotenv(dotenv_path)  # 载入环境变量
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    from module.super_okx import GeniusTrader
    from utils.files import find_or_create_doc

    # target_stock = "LUNC-USDT"
    # target_stock = "BTC-USDT"
    target_stock = "ETH-USDT"
    # target_stock = "FLOKI-USDT"
    # target_stock = "OMI-USDT"
    # target_stock = "DOGE-USDT"
    # target_stock = "PEPE-USDT"
    # target_stock = "RACA-USDT"

    pre_day = None
    # pre_day = 1715587200000

    genius_trader = GeniusTrader()
    long_period_candle = []
    for _ in range(23):
        # period = "1H"
        period = "4H"
        total_candle = genius_trader.stock_candle(target_stock, after=pre_day, period=period)
        # total_candle.reverse()  # 由于时间，倒序
        pre_day = total_candle[-1][0]
        print(pre_day)
        print()
        long_period_candle.extend(total_candle)

    long_period_candle.reverse()
    # print(long_period_candle)
    # for i in long_period_candle:
    #     print(i)
    # print(len(long_period_candle))

    total_path = os.path.join(BASE_DIR, f"./data/{target_stock}.json")
    # total_path = os.path.join(BASE_DIR, f"./data/{target_stock}-longtest.json")
    find_or_create_doc(total_path, 'json')
    json_data = json.dumps(long_period_candle)
    with open(total_path, 'w', encoding='utf-8') as f:
        f.write(json_data)

    with open(total_path, 'r') as file:
        loaded_data = json.load(file)
    # print(loaded_data)

