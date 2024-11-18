# 导入日志配置
import json
import logging.config
from datetime import datetime

from utils.logging_config import Logging_dict

logging.config.dictConfig(Logging_dict)
LOGGING = logging.getLogger("app_01")

import redis


class Account_info:
    def __init__(self):
        self.init_balance = 100
        self.balance = self.init_balance
        self.total_ratio = 1.0
        self.risk_rate = 0.01

        self.long_position = 0
        self.max_long_position = 3

        self.hold_price = 0
        self.init_hold_price = 0

        self.hold_amount = 0
        self.max_hold_amount = 0

    def print_all_info(self):
        # 获取类的所有属性及其值
        attributes = vars(self)
        for attr, value in attributes.items():
            print(f"{attr}: {value}")
        print(self.balance + self.hold_amount * self.hold_price)

    # def update_account(self, params):
    #     self.balance = params['balance']
    #
    # def update_hold(self, params):
    #     self.long_position = params['long_position']
    #     self.hold_price = params['hold_price']

    def update_info(self, params):
        self.balance = params['balance']
        self.long_position = params['long_position']
        self.hold_price = params['hold_price']
        self.hold_amount = params['hold_amount']

        if "init_hold_price" in params:
            self.init_hold_price = params['init_hold_price']

        if "init_balance" in params:
            self.init_balance = params['init_balance']

        if "max_hold_amount" in params:
            self.max_hold_amount = params['max_hold_amount']

        if "total_ratio" in params:
            self.total_ratio = params['total_ratio']


def sell222(account_info, market_price, ratio=1.0):
    # amount = account_info.max_hold_amount * ratio if ratio < 1.0 else account_info.hold_amount
    amount = account_info.hold_amount
    position = account_info.long_position
    if ratio == 1.0:
        position = 0
    if ratio < 1.0:
        amount = round(account_info.max_hold_amount * ratio, 5)
        if account_info.total_ratio < ratio:  # 不足部分全清
            print("清空")
            position = 0
            amount = account_info.hold_amount

    receive_money = amount * market_price
    print(f"amount: {amount}, price: {market_price}")

    account_info.update_info(
        {
            "balance": account_info.balance + receive_money,
            "long_position": position,
            # "hold_price": 0,
            "hold_price": account_info.hold_price,
            "hold_amount": account_info.hold_amount - amount,
            "total_ratio": account_info.total_ratio - ratio
        }
    )
    print(f"balance:{account_info.balance}")


def sell(account_info, market_price, ratio=1.0):
    amount = account_info.hold_amount
    if ratio < 1.0:
        amount = round(account_info.max_hold_amount * ratio, 5)
    if account_info.total_ratio < ratio:  # 不足部分全清
        print("清空")
        amount = account_info.hold_amount

    position = account_info.long_position
    receive_money = amount * market_price
    print(f"amount: {amount}, price: {market_price}")

    new_params = {
        "balance": account_info.balance + receive_money,
        "long_position": position,
        "hold_price": account_info.hold_price,
        "hold_amount": account_info.hold_amount - amount,
        "total_ratio": account_info.total_ratio - ratio
    }
    account_ratio = account_info.total_ratio
    if ratio == 1.0 or account_ratio < ratio:
        # print(ratio,account_info.total_ratio)

        new_params["hold_price"] = 0
        new_params["long_position"] = 0
        new_params["total_ratio"] = 0
        new_params["hold_amount"] = 0
        new_params["max_hold_amount"] = 0
    account_info.update_info(new_params)

    if ratio == 1.0 or account_ratio < ratio:
        init_balance = account_info.init_balance
        balance = account_info.balance
        delta = balance - init_balance
        formatted_value = '{:.2%}'.format(delta / init_balance)
        print(f"{balance}, {init_balance}")
        print(f"!收益率: {formatted_value}")  # 输出: 75.00%
    print(f"balance:{round(account_info.balance,10)}")



if __name__ == '__main__':

    import os
    from pathlib import Path
    from dotenv import load_dotenv

    project_path = Path(__file__).resolve().parent  # 此脚本的运行"绝对"路径
    dotenv_path = os.path.join(project_path, '../.env.dev')  # 指定.env.dev文件的路径
    load_dotenv(dotenv_path)  # 载入环境变量
    BASE_DIR = Path(__file__).resolve().parent.parent

    from module.genius_trading import GeniusTrader
    from module.common_index import get_DochianChannel, get_ATR

    target_stock = "LUNC-USDT"
    target_stock = "BTC-USDT"
    target_stock = "FLOKI-USDT"
    target_stock = "OMI-USDT"
    target_stock = "DOGE-USDT"
    target_stock = "PEPE-USDT"


    genius_trader = GeniusTrader()
    # total_candle = genius_trader.stock_candle(target_stock)
    # total_candle.reverse()  # 由于时间，倒序

    total_path = os.path.join(BASE_DIR, f"./data/{target_stock}.json")
    with open(total_path, 'r') as file:
        long_period_candle = json.load(file)
    # print(long_period_candle)


    s = 1
    print()
    PERIOD = 5

    account_info = Account_info()

    for day in range(len(long_period_candle)):
        if day >= PERIOD and s == 1:
            print(day)
            # s=0
            pre_candle = long_period_candle[day - PERIOD:day]
            # for i in pre_candle:
            #     print(i)

            history_max_price, history_min_price = get_DochianChannel(pre_candle, PERIOD)
            ATR = get_ATR(pre_candle, PERIOD)
            print(f"max: {history_max_price}, \nmin: {history_min_price}, \nATR: {ATR}")

            today_candle = long_period_candle[day][1:]  # 第一项是时间戳，要移除
            today_candle = [float(item) for item in today_candle]
            today_max_price = max(today_candle)
            today_min_price = min(today_candle)
            print(f"t_max: {today_max_price}, \nt_min: {today_min_price}")

            position = account_info.long_position
            target_market_price = history_max_price
            if today_max_price > target_market_price and position == 0:
                # print(f"$$$today_max_price:{today_max_price}")
                print("建仓")

                amount = round(account_info.risk_rate * account_info.init_balance / ATR, 5)
                total_cost = amount * target_market_price
                print(f"amount: {amount}, price: {target_market_price}")

                account_info.update_info(
                    {
                        "balance": account_info.balance - total_cost,
                        "init_balance": account_info.balance,
                        "long_position": position + 1,
                        "hold_amount": account_info.hold_amount + amount,
                        "max_hold_amount": account_info.hold_amount + amount,
                        "hold_price": target_market_price,
                        "init_hold_price": target_market_price,
                        "total_ratio": 1.0
                    }
                )
                print(f"balance:{round(account_info.balance, 10)}")

            for _ in range(account_info.max_long_position):
                position = account_info.long_position
                target_market_price = round(account_info.init_hold_price + position * 0.5 * ATR, 10)
                if today_max_price > target_market_price and 0 < position <= account_info.max_long_position:
                    print("加仓")

                    amount = round(account_info.risk_rate * account_info.init_balance / ATR, 5)
                    total_cost = amount * target_market_price
                    print(f"amount: {amount}, price: {target_market_price}")

                    account_info.update_info(
                        {
                            "balance": account_info.balance - total_cost,
                            "long_position": position + 1,
                            "hold_price": target_market_price,
                            "hold_amount": account_info.hold_amount + amount,
                            "max_hold_amount": account_info.hold_amount + amount,
                        }
                    )
                    print(f"balance:{round(account_info.balance, 10)}")

            # position = account_info.long_position
            # target_market_price = round(account_info.hold_price - 1.5 * ATR, 10)
            # if today_min_price < target_market_price and position > 0:
            #     print("平仓(+0N线, 动态追踪止损)")
            #     sell(account_info, target_market_price)

            position = account_info.long_position
            target_market_price = round(account_info.init_hold_price + 2 * ATR, 10)
            if today_max_price > target_market_price and position > 0:
                print("减仓(+2N线, 分批止盈)")
                sell(account_info, target_market_price, ratio=0.3)

            position = account_info.long_position
            target_market_price = round(account_info.init_hold_price + 3 * ATR, 10)
            if today_max_price > target_market_price and position > 0:
                print("减仓(+3N线, 分批止盈)")
                sell(account_info, target_market_price, ratio=0.3)

            position = account_info.long_position
            target_market_price = round(account_info.init_hold_price + 4 * ATR, 10)
            if today_max_price > target_market_price and position > 0:
                print("减仓(+4N线, 分批止盈)")
                sell(account_info, target_market_price, ratio=0.2)

            position = account_info.long_position
            target_market_price = round(account_info.init_hold_price + 5 * ATR, 10)
            if today_max_price > target_market_price and position > 0:
                print("平仓(+5N线, 止盈)")
                sell(account_info, target_market_price, ratio=0.2)

            position = account_info.long_position
            target_market_price = history_min_price
            if today_min_price < target_market_price and position > 0:
                print("平仓(唐奇安下通道, 止盈)")
                sell(account_info, target_market_price)

            position = account_info.long_position
            target_market_price = round(account_info.init_hold_price - 2 * ATR, 10)
            if today_min_price < target_market_price and position > 0:
                print("平仓(-2N线, 初始止损)")
                sell(account_info, target_market_price)

            print()

        # print()

    account_info.print_all_info()
