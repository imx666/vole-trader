# 导入日志配置
import logging.config
import time
from datetime import datetime

from utils.logging_config import Logging_dict

logging.config.dictConfig(Logging_dict)
LOGGING = logging.getLogger("app_01")

import redis

from utils.url_center import redis_url_fastest
from monitor.account_monitor import HoldInfo

redis_okx = redis.Redis.from_url(redis_url_fastest)

if __name__ == '__main__':
    # 指定.env.dev文件的路径
    from pathlib import Path
    from dotenv import load_dotenv

    project_path = Path(__file__).resolve().parent  # 此脚本的运行"绝对"路径
    import os

    dotenv_path = os.path.join(project_path, '../.env.dev')
    load_dotenv(dotenv_path)  # 载入环境变量




    target_stock = "BTC-USDT"
    target_stock = "DOGE-USDT"
    target_stock = "ETH-USDT"
    # target_stock = "FLOKI-USDT"
    # target_stock = "OMI-USDT"
    # target_stock = "PEPE-USDT"
    target_stock = "XRP-USDT"
    # target_stock = "LUNC-USDT"


    # 初始化
    redis_okx.hset(f"hold_info:{target_stock}",
                   mapping={
                       'execution_cycle': "ready",
                       'pending_order': 0,
                       'tradeFlag': 'all-auth',
                       'long_position': 0,
                       'sell_times': 0,
                       '<init_balance>': 100,
                       '<risk_rate>': 0.0035,
                       '<max_long_position>': 3,
                       '<max_sell_times>': 3,
                   })

    hold_info = HoldInfo(target_stock)



    # # 重启redis时
    # from module.trade_records import TradeRecordManager
    # # execution_cycle = sqlManager.last_execution_cycle(strategy_name)  # 获取编号
    # # execution_cycle = "自己看数据库是哪个编号"
    # execution_cycle = "TURTLE-FLOKI-20241221_0001"
    # sqlManager = TradeRecordManager(target_stock, strategy_name="TURTLE")
    # # execution_cycle = "ready"
    # long_position = sqlManager.get(execution_cycle, "long_position")
    # sell_times = sqlManager.get(execution_cycle, "sell_times")
    # build_price = sqlManager.get(execution_cycle, "build_price"),
    # balance_delta = sqlManager.get(execution_cycle, "balance_delta")  # 虽然需要传编号，但是计算价差是用不着的
    # init_balance = 100 + balance_delta
    # print(init_balance)
    # print(balance_delta)
    #
    # redis_okx.hset(f"hold_info:{target_stock}",
    #                mapping={
    #                    'execution_cycle': execution_cycle,
    #                    'pending_order': 0,  # pending_order是防止重复挂建仓订单的
    #                    'tradeFlag': 'all-auth',
    #                    'long_position': long_position,
    #                    'sell_times': sell_times,
    #                    '<init_balance>': init_balance,
    #                    '<risk_rate>': 0.0035,
    #                    '<max_long_position>': 3,
    #                    '<max_sell_times>': 3,
    #                })
