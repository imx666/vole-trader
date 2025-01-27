import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# 锁定系统运行路径
project_path = Path(__file__).resolve().parent  # 此脚本的运行"绝对"路径
dotenv_path = os.path.join(project_path, '../')
sys.path.append(dotenv_path)

dotenv_path = os.path.join(project_path, '../../.env.dev')  # 指定.env.dev文件的路径
load_dotenv(dotenv_path)  # 载入环境变量

from module.super_okx import beijing_time
from module.common_index import get_ATR, Amplitude, compute_market_deal
from candle.draw_trade_picture import draw_picture

BASE_DIR = Path(__file__).resolve().parent.parent


DEAL_RATE = 0.0005  # 交易手续费
STOP_LOSS_RATE = 0.03  # 止损率


class Account_info:
    def __init__(self):
        self.init_balance = 100
        self.balance = self.init_balance
        self.total_ratio = 1.0
        # self.risk_rate = 0.01
        # self.risk_rate = 0.003  # 由于时间周期减小，风险率也要减小,1H
        self.risk_rate = 0.0025  # 由于时间周期减小，风险率也要减小,4H
        self.total_cost = 0

        self.long_position = 0
        self.max_long_position = 2

        self.max_sell_times = 3
        self.sell_times = 0

        self.hold_price = 0
        self.open_price = 0

        self.hold_amount = 0
        self.max_hold_amount = 0

        self.return_rate_list = []

        self.make_money_times = 0
        self.lost_money_times = 0

        self.make_money_rate = 0
        self.lost_money_rate = 0

    def print_all_info(self):
        # 获取类的所有属性及其值
        attributes = vars(self)
        for attr, value in attributes.items():
            if attr == 'return_rate_list':
                continue
            print(f"{attr}: {value}")
        print(self.balance + self.hold_amount * self.hold_price)

        # return attributes
        return self.balance + self.hold_amount * self.hold_price

    def update_info(self, params):
        self.balance = params['balance']
        self.long_position = params['long_position']
        self.hold_price = params['hold_price']
        self.hold_amount = params['hold_amount']

        if "open_price" in params:
            self.open_price = params['open_price']

        if "init_balance" in params:
            self.init_balance = params['init_balance']

        if "max_hold_amount" in params:
            self.max_hold_amount = params['max_hold_amount']

        if "total_ratio" in params:
            self.total_ratio = params['total_ratio']

        if "sell_times" in params:
            self.sell_times = params['sell_times']

        if "total_cost" in params:
            self.total_cost = params['total_cost']


def sell(account_info, market_price, ratio=1.0, today_timestamp=None):
    amount = account_info.hold_amount
    if ratio < 1.0:
        amount = round(account_info.max_hold_amount * ratio, 5)
    if account_info.total_ratio < ratio:  # 不足部分全清
        print("清空")
        amount = account_info.hold_amount

    # 部分卖出
    position = account_info.long_position
    receive_money = amount * market_price
    receive_money = receive_money * (1 - DEAL_RATE)

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
        new_params["total_cost"] = 0
        new_params["init_balance"] = account_info.balance + receive_money

    if ratio == 1.0 or account_ratio < ratio:
        # init_balance = account_info.init_balance
        # balance = account_info.balance + receive_money
        # delta = balance - init_balance
        # formatted_value = '{:.2%}'.format(delta / init_balance)
        # print(f"{round(balance, 3)}, {round(init_balance, 3)}")
        # print(f"!收益率: {formatted_value}")
        # account_info.return_rate_list.append([today_timestamp, round(delta / init_balance, 4)])

        total_cost = account_info.total_cost
        not_use_money = account_info.init_balance - total_cost
        total_increase = account_info.balance + receive_money - not_use_money
        delta = total_increase - total_cost
        formatted_value = '{:.2%}'.format(delta / total_cost)
        print(f"{round(total_increase, 3)}, {round(total_cost, 3)}")
        print(f"!收益率: {formatted_value}")
        if delta > 0:
            account_info.make_money_times += 1
            account_info.make_money_rate += delta / total_cost
        else:
            account_info.lost_money_times += 1
            account_info.lost_money_rate -= delta / total_cost

        account_info.return_rate_list.append([today_timestamp, round(delta / total_cost, 4)])

    account_info.update_info(new_params)
    print(f"balance: {round(account_info.balance, 3)}")


def execution_plan(PERIOD, PERIOD_up, PERIOD_down, target_stock, long_period_candle, total_path, draw=False):
    with open('market_monitor.json', 'r') as file:
        target_stock_dict = json.load(file)

    target_stock_info = target_stock_dict[target_stock]
    newest_price = target_stock_info["last"]
    market_cap = target_stock_info["marketCap"]

    buy_days = []
    sell_days = []
    sell_empty_days = []

    account_info = Account_info()
    close_price = 0

    for day in range(len(long_period_candle)):
        if day < PERIOD:
            continue

        today_candle = long_period_candle[day]
        today_timestamp = today_candle[0]

        # print(f"{day}, today: {beijing_time(today_timestamp)}")
        today_candle = [float(item) for item in today_candle]
        open_price = today_candle[1]
        today_max_price = today_candle[2]
        today_min_price = today_candle[3]

        position = account_info.long_position
        pre_pre_candle = long_period_candle[day - PERIOD_up * 2:day - PERIOD_up]
        pre_candle = long_period_candle[day - PERIOD_up:day]
        target_market_price = open_price
        auth, li = Amplitude(pre_candle, "up")
        if auth and position == 0:

            # 市值小于0.1亿，不建仓
            previous_market_cap = market_cap * today_min_price / newest_price
            if previous_market_cap < 0.1 * 10 ** 8:
                print(f"市值小于0.1亿，不建仓,market_cap:{previous_market_cap}")
                continue

            pre_pre = compute_market_deal(pre_pre_candle)
            pre = compute_market_deal(pre_candle)
            if pre / pre_pre < 0.5:
                continue
            
            # if sum(li) - PERIOD_up < 0.01:
            #     continue

            print(f"\n\n\n\n{day}, today: {beijing_time(today_timestamp)}")
            print("建仓")
            print(li, sum(li) - PERIOD_up)
            for i in li:
                if i < 1:
                    print("#" * 50)

            buy_days.append([today_timestamp, target_market_price])
            close_price = target_market_price * (1 - STOP_LOSS_RATE)
            print(pre_pre, pre, pre / pre_pre)

            # amount = round(account_info.risk_rate * account_info.init_balance / ATR, 5)
            # total_cost = amount * target_market_price
            #
            # expect_max_cost = account_info.init_balance * 0.3
            # if total_cost > expect_max_cost:
            #     print("超预算(减少数量)")
            #     amount = expect_max_cost / target_market_price
            #     total_cost = expect_max_cost
            #
            # expect_min_cost = account_info.init_balance * 0.24
            # if total_cost < expect_min_cost:
            #     print("不足预算(增加数量)")
            #     amount = expect_min_cost / target_market_price
            #     total_cost = expect_min_cost

            amount = round(account_info.init_balance * 0.99 / target_market_price, 8)
            amount = amount * (1 - DEAL_RATE)
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
                    "total_cost": account_info.total_cost + total_cost,
                    "open_price": target_market_price,
                    "total_ratio": 1.0
                }
            )
            print(f"balance:{round(account_info.balance, 3)}")
            print()
            continue

        position = account_info.long_position
        target_market_price = open_price
        pre_candle = long_period_candle[day - PERIOD_down:day]
        if Amplitude(pre_candle, "down") and position > 0:
            print(f"{day}, today: {beijing_time(today_timestamp)}")
            print("平仓")
            sell_empty_days.append([today_timestamp, target_market_price])
            sell(account_info, target_market_price, today_timestamp=today_timestamp)
            print()
            continue

        position = account_info.long_position
        target_market_price = close_price
        if today_min_price < target_market_price < today_max_price and position > 0:
            print(f"{day}, today: {beijing_time(today_timestamp)}")
            print("平仓(半线)")
            sell_empty_days.append([today_timestamp, target_market_price])
            sell(account_info, target_market_price, today_timestamp=today_timestamp)
            print()
            continue

    hold_market_price = account_info.print_all_info()

    if draw:
        draw_picture(total_path, target_stock, buy_days, sell_days, sell_empty_days, start_day, end_day,
                     return_rate_list=account_info.return_rate_list)

    report_dict = {
        "标的": target_stock,
        "收益": hold_market_price,
        "盈利次数": account_info.make_money_times,
        "亏损次数": account_info.lost_money_times,
        "盈亏比": (account_info.make_money_rate / account_info.make_money_times) / (
                    account_info.lost_money_rate / account_info.lost_money_times)
    }
    return report_dict


if __name__ == '__main__':
    os.system("clear")
    target_stock = os.getenv("target_stock")

    PERIOD = 3
    PERIOD_up = 6
    PERIOD_down = 3

    start_day = 3000
    end_day = 9600
    end_day = 7600
    end_day = 60 * 96

    # target_stock = "BTC-USDT"
    # target_stock = "LUNC-USDT"
    # target_stock = "ETH-USDT"
    # target_stock = "FLOKI-USDT"
    # target_stock = "OMI-USDT"
    # target_stock = "DOGE-USDT"
    # target_stock = "PEPE-USDT"

    target_stock = "JST-USDT"  # 117
    target_stock = "ZRX-USDT"  # 95
    target_stock = "ZIL-USDT"  # 115
    # target_stock = "BOME-USDT"  # 表现很不好
    # target_stock = "ARKM-USDT"  # 表现很不好
    # target_stock = "ORDI-USDT"  # 119
    # target_stock = "ZRO-USDT"  # 124
    # target_stock = "MEW-USDT"  # 116

    total_path = os.path.join(BASE_DIR, f"../data/15m/{target_stock}.json")

    with open(total_path, 'r') as file:
        long_period_candle = json.load(file)
        print("k线数量: ", len(long_period_candle))

    long_period_candle = long_period_candle[start_day:end_day]
    execution_plan(PERIOD, PERIOD_up, PERIOD_down, target_stock, long_period_candle, total_path, draw=True)
