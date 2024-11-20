# 导入日志配置
import json
import logging.config
from datetime import datetime

from utils.logging_config import Logging_dict

logging.config.dictConfig(Logging_dict)
LOGGING = logging.getLogger("app_01")


# import redis


class Account_info:
    def __init__(self):
        self.init_balance = 100
        self.balance = self.init_balance
        self.total_ratio = 1.0
        self.risk_rate = 0.01

        self.long_position = 0
        self.max_long_position = 3

        self.max_sell_times = 3
        self.sell_times = 0

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

        if "sell_times" in params:
            self.sell_times = params['sell_times']


def sell(account_info, market_price, ratio=1.0):
    amount = account_info.hold_amount
    if ratio < 1.0:
        amount = round(account_info.max_hold_amount * ratio, 5)
    if account_info.total_ratio < ratio:  # 不足部分全清
        print("清空")
        amount = account_info.hold_amount

    # 部分卖出
    position = account_info.long_position
    receive_money = amount * market_price
    print(f"amount: {amount}, price: {market_price}")

    new_params = {
        "balance": account_info.balance + receive_money,
        "long_position": position,
        "hold_price": account_info.hold_price,
        "hold_amount": account_info.hold_amount - amount,
        "total_ratio": account_info.total_ratio - ratio,
        "sell_times": account_info.sell_times + 1
    }

    # 全部卖出
    account_ratio = account_info.total_ratio
    if ratio == 1.0 or account_ratio < ratio:
        new_params["hold_price"] = 0
        new_params["long_position"] = 0
        new_params["total_ratio"] = 0
        new_params["hold_amount"] = 0
        new_params["max_hold_amount"] = 0
        new_params["sell_times"] = 0
        new_params["init_balance"] = account_info.balance + receive_money

    if ratio == 1.0 or account_ratio < ratio:
        init_balance = account_info.init_balance
        balance = account_info.balance + receive_money
        delta = balance - init_balance
        formatted_value = '{:.2%}'.format(delta / init_balance)
        print(f"{round(balance, 3)}, {round(init_balance, 3)}")
        print(f"!收益率: {formatted_value}")

    account_info.update_info(new_params)
    print(f"balance: {round(account_info.balance, 3)}")


if __name__ == '__main__':

    import os
    from pathlib import Path
    from dotenv import load_dotenv

    project_path = Path(__file__).resolve().parent  # 此脚本的运行"绝对"路径
    dotenv_path = os.path.join(project_path, '../.env.dev')  # 指定.env.dev文件的路径
    load_dotenv(dotenv_path)  # 载入环境变量
    BASE_DIR = Path(__file__).resolve().parent.parent

    # from module.genius_trading import GeniusTrader
    from module.common_index import get_DochianChannel, get_ATR

    target_stock = "LUNC-USDT"
    target_stock = "BTC-USDT"
    target_stock = "FLOKI-USDT"
    target_stock = "OMI-USDT"
    target_stock = "DOGE-USDT"
    target_stock = "PEPE-USDT"

    # genius_trader = GeniusTrader()
    # total_candle = genius_trader.stock_candle(target_stock)
    # total_candle.reverse()  # 由于时间，倒序

    total_path = os.path.join(BASE_DIR, f"./data/{target_stock}.json")
    with open(total_path, 'r') as file:
        long_period_candle = json.load(file)

    PERIOD = 5
    buy_days = []
    sell_days = []
    sell_empty_days = []

    account_info = Account_info()
    for day in range(len(long_period_candle)):
        if day < PERIOD:
        # if day < 200 or day > 350:
            continue

        # if day >= PERIOD:
        print(day)
        flag = 0

        pre_candle = long_period_candle[day - PERIOD:day]
        history_max_price, history_min_price = get_DochianChannel(pre_candle, PERIOD)
        ATR = get_ATR(pre_candle, PERIOD)
        print(f"max: {history_max_price}, \nmin: {history_min_price}, \nATR: {ATR}")

        # today_candle = long_period_candle[day][1:]  # 第一项是时间戳，要移除
        # today_max_price = max(today_candle)
        # today_min_price = min(today_candle)
        today_candle = long_period_candle[day]  # 第一项是时间戳，要移除
        today_timestamp = today_candle[0]
        today_candle = [float(item) for item in today_candle]
        today_max_price = today_candle[2]
        today_min_price = today_candle[3]
        print(f"t_max: {today_max_price}, \nt_min: {today_min_price}")

        position = account_info.long_position
        target_market_price = history_max_price
        if today_max_price > target_market_price and position == 0:
            print("建仓")
            flag = 1
            buy_days.append([today_timestamp, target_market_price])

            amount = round(account_info.risk_rate * account_info.init_balance / ATR, 5)
            total_cost = amount * target_market_price
            print(f"amount: {amount}, price: {target_market_price}")
            print(f"total_cost: {round(total_cost, 3)}")

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
            print(f"balance:{round(account_info.balance, 3)}")

        for _ in range(account_info.max_long_position):
            position = account_info.long_position
            target_market_price = round(account_info.init_hold_price + position * 0.5 * ATR, 10)
            if today_max_price > target_market_price and 0 < position <= account_info.max_long_position:
                print("加仓")
                flag = 1
                buy_days.append([today_timestamp, target_market_price])

                amount = round(account_info.risk_rate * account_info.init_balance / ATR, 5)
                total_cost = amount * target_market_price
                print(f"amount: {amount}, price: {target_market_price}")
                print(f"total_cost: {round(total_cost, 3)}")

                account_info.update_info(
                    {
                        "balance": account_info.balance - total_cost,
                        "long_position": position + 1,
                        "hold_price": target_market_price,
                        "hold_amount": account_info.hold_amount + amount,
                        "max_hold_amount": account_info.hold_amount + amount,
                    }
                )
                print(f"balance:{round(account_info.balance, 3)}")

        for _ in range(account_info.max_sell_times):
            position = account_info.long_position
            sell_time = account_info.sell_times
            target_market_price = round(account_info.init_hold_price + (sell_time + 2) * ATR, 10)
            if today_max_price > target_market_price and position > 0:
                print(f"减仓(+{sell_time + 2}N线, 分批止盈)")
                sell_days.append([today_timestamp, target_market_price])

                ratio = 0.3 if sell_time <= 1 else 0.2
                print(f"ratio: {ratio}")
                sell(account_info, target_market_price, ratio=ratio)

        # position = account_info.long_position
        # target_market_price = round(account_info.init_hold_price + 2 * ATR, 10)
        # if today_max_price > target_market_price and position > 0:
        #     print("减仓(+2N线, 分批止盈)")
        #     sell(account_info, target_market_price, ratio=0.3)

        # position = account_info.long_position
        # if position > 0 and flag == 0:
        #     hold_average_price = (account_info.init_balance - account_info.balance) / account_info.hold_amount
        #     target_market_price = round(hold_average_price - 0.5 * ATR, 10)
        #     if today_min_price < target_market_price and position > 0:
        #         print("平仓(+0N线, 动态追踪止损)")
        #         sell_empty_days.append([today_timestamp, target_market_price])
        #
        #         sell(account_info, target_market_price)

        position = account_info.long_position
        target_market_price = history_min_price
        if today_min_price < target_market_price and position > 0:
            print("平仓(唐奇安下通道5, 止盈)")
            sell_empty_days.append([today_timestamp, target_market_price])

            sell(account_info, target_market_price)

        # position = account_info.long_position
        # _, history_min_price = get_DochianChannel(pre_candle, 3)
        # target_market_price = history_min_price
        # if today_min_price < target_market_price and position > 0:
        #     print("平仓(唐奇安下通道3, 止盈)")
        #     sell_empty_days.append([today_timestamp, target_market_price])
        #
        #     sell(account_info, target_market_price)

        position = account_info.long_position
        target_market_price = round(account_info.init_hold_price - 2 * ATR, 10)
        if today_min_price < target_market_price and position > 0:
            print("平仓(-2N线, 初始止损)")
            sell_empty_days.append([today_timestamp, target_market_price])

            sell(account_info, target_market_price)

        print()

    account_info.print_all_info()

    print(buy_days)
    print(sell_days)
    print(sell_empty_days)
