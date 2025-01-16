import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

# 锁定系统运行路径
project_path = Path(__file__).resolve().parent  # 此脚本的运行"绝对"路径
dotenv_path = os.path.join(project_path, '../')
sys.path.append(dotenv_path)

dotenv_path = os.path.join(project_path, '../../.env.dev')  # 指定.env.dev文件的路径
load_dotenv(dotenv_path)  # 载入环境变量

BASE_DIR = Path(__file__).resolve().parent.parent

from simulate.simulate_SPRINTER import execution_plan

os.system("clear")
os.system("clear")
time.sleep(2)

# target_stock = "BTC-USDT"
# target_stock = "ETH-USDT"
# target_stock = "DOGE-USDT"


target_stock_li = [
    # "PEPE-USDT",
    # "FLOKI-USDT",
    "LUNC-USDT",
    # "OMI-USDT",
    "ZRX-USDT",
    # "RACA-USDT",
    "JST-USDT",
    "ZIL-USDT",
    "ORDI-USDT",
    "MEW-USDT",
    "ZRO-USDT"
]

PERIOD = 3
PERIOD_up = 6
PERIOD_down = 3

start_day = 3000
end_day = 9600
end_day = 7600

final_balance_li = []
for target_stock in target_stock_li:
    total_path = os.path.join(BASE_DIR, f"../data/15m/{target_stock}.json")
    with open(total_path, 'r') as file:
        long_period_candle = json.load(file)
        print(len(long_period_candle))

    long_period_candle = long_period_candle[start_day:end_day]
    report_dict = execution_plan(PERIOD, PERIOD_up, PERIOD_down, target_stock, long_period_candle, total_path)

    final_balance_li.append(report_dict)

print("\n\n")
for report_dict in final_balance_li:
    for attr, value in report_dict.items():
        print(f"{attr}: {value}")
    print()



