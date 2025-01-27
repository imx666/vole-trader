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

from simulate.simulate_TURTLE import execution_plan

os.system("clear")
os.system("clear")
time.sleep(2)

# target_stock = "BTC-USDT"
# target_stock = "ETH-USDT"
# target_stock = "DOGE-USDT"


target_stock_li = [
    "PEPE-USDT",
    "FLOKI-USDT",
    # "LUNC-USDT",
    # "OMI-USDT",
    # "ZRX-USDT",
    # "RACA-USDT",
    # "JST-USDT",
    # "ZIL-USDT",
    # "ORDI-USDT"
]

with open('market_monitor.json', 'r') as file:
    target_stock_dict = json.load(file)

target_stock_li = list(target_stock_dict.keys())
PERIOD = 3

start_day = 0
end_day = 30 * 6

start_day = 0
end_day = 60 * 6

# start_day = 0
# end_day = 180 * 6

# start_day = 180 * 6
# end_day = -1
#
# start_day = 270 * 6
# end_day = -1
#
# start_day = 0
# end_day = -1

final_balance_li = []
for target_stock in target_stock_li:
    try:
        total_path = os.path.join(BASE_DIR, f"../data/4H/{target_stock}.json")
        with open(total_path, 'r') as file:
            long_period_candle = json.load(file)
            print(len(long_period_candle))

        long_period_candle = long_period_candle[start_day:end_day]
        report_dict = execution_plan(PERIOD, target_stock, long_period_candle, total_path)

        final_balance_li.append(report_dict)
    except Exception as e:
        print("error",e)
        continue

print("\n\n")
sb_li = []
win_times, lose_times = 0, 0
for report_dict in final_balance_li:
    for attr, value in report_dict.items():
        print(f"{attr}: {value}")
        if attr == "收益":
            sb_li.append(value)
        if attr == "盈利次数":
            win_times += value
        if attr == "亏损次数":
            lose_times += value
    print()

print('-'*30)
print("币种个数",len(sb_li))
print(sum(sb_li)/len(sb_li))
print("盈利次数", win_times)
print("亏损次数", lose_times)

# 前半年
# [237.38133259490223, 140.07085975561776, 86.95257647125578, 127.68773773510372, 141.06654183715568, 168.90808711706413, 134.1064482136139, 92.50645596710571, 112.04034100669023]

# 后半年
# [116.9448404225082, 113.28719786538005, 105.68720803057907, 153.7010068043457, 92.25004578671289, 130.3006217082878, 120.31104419168076, 147.31498428245786, 118.28611720881275]

# 全年
# [277.6060137490649, 158.6823292168699, 91.8976197548802, 196.2573596337263, 130.1339488379918, 220.08832605830045, 161.34486815142225, 136.27587157545778, 132.5281360944362]

