import redis
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 锁定系统运行路径
project_path = Path(__file__).resolve().parent  # 此脚本的运行"绝对"路径
dotenv_path = os.path.join(project_path, '../')
sys.path.append(dotenv_path)

dotenv_path = os.path.join(project_path, '../../.env.dev')  # 指定.env.dev文件的路径
load_dotenv(dotenv_path)  # 载入环境变量


from utils.url_center import redis_url
from monitor.account_monitor import HoldInfo
from module.trade_assistant import hold_info
from module.trade_records import TradeRecordManager

redis_okx = redis.Redis.from_url(redis_url)
if __name__ == '__main__':


    # target_stock = "LUNC-USDT"
    # target_stock = "BTC-USDT"
    # target_stock = "DOGE-USDT"
    # target_stock = "ETH-USDT"
    # target_stock = "FLOKI-USDT"
    # target_stock = "OMI-USDT"
    # target_stock = "PEPE-USDT"
    target_stock = "XRP-USDT"


    sqlManager = TradeRecordManager(target_stock, "TURTLE")
    execution_cycle = "TURTLE-XRP-20250101_0001"
    long_position = sqlManager.get(execution_cycle, "long_position")
    print(long_position)
    # long_position = sqlManager.get_trade_record("TURTLE-FLOKI-20250103_0001")
    # print(long_position)
    delta, profit_rate = sqlManager.get(execution_cycle, "delta")  # 虽然需要传编号，但是计算价差是用不着的
    print(delta, profit_rate)
