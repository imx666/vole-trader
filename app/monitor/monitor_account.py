import json
import sys
import time
import hmac
import hashlib
import base64
from datetime import datetime
import os
import redis

from pathlib import Path
from dotenv import load_dotenv

# 锁定系统运行路径
project_path = Path(__file__).resolve().parent  # 此脚本的运行"绝对"路径
dotenv_path = os.path.join(project_path, '../')
sys.path.append(dotenv_path)
print(dotenv_path)

dotenv_path = os.path.join(project_path, '../../.env.dev')  # 指定.env.dev文件的路径
load_dotenv(dotenv_path)  # 载入环境变量

api_key = os.getenv('API_KEY')
secret_key = os.getenv('SECRET_KEY')
passphrase = os.getenv('PASSPHRASE')

import logging.config
from utils.logging_config import Logging_dict

logging.config.dictConfig(Logging_dict)
LOGGING = logging.getLogger("app_01")

from MsgSender.wx_msg import send_wx_info
from module.redis_url import redis_url
from module.genius_trading import GeniusTrader
from module.trade_records import TradeRecordManager


class HoldInfo:
    def __init__(self, target_stock):
        self.target_stock = target_stock
        self.redis_okx = redis.Redis.from_url(redis_url)
        self.decoded_data = {}
        self.newest_all()

    def newest(self, op):
        target_op = self.redis_okx.hget(f"hold_info:{self.target_stock}", op)
        # return target_op.decode() if target_op is not None else None
        if target_op is None:
            raise Exception(f"HoldInfo: redis: 键'{op}'不存在")

        target_value = target_op.decode('utf-8')

        if op in origin_str_list:
            return target_value
        elif op in origin_int_list:
            return int(target_value)
        else:
            return float(target_value)
        # return float(target_op.decode()) if target_op is not None else None

    def get(self, key):
        target_value = self.decoded_data.get(key, None)
        return target_value

    def remove(self, key):
        response = self.redis_okx.hdel(f"hold_info:{self.target_stock}", key)
        if response:
            print("remove success")
        # else:
        #     raise Exception(f"HoldInfo: redis: {self.target_stock} remove '{key}' failed, 请检查键是否存在")

    def pull(self, key, value):
        target_value = self.decoded_data.get(key, None)

        # 一样的就不用上传
        if target_value == value:
            return

        self.redis_okx.hset(f"hold_info:{self.target_stock}", key, value)
        self.newest_all()

    def pull_dict(self, target_dict):
        self.redis_okx.hset(f"hold_info:{self.target_stock}", mapping=target_dict)
        self.newest_all()
        LOGGING.info("信息同步redis成功")

    def newest_all(self):
        all_info = self.redis_okx.hgetall(f"hold_info:{self.target_stock}")
        if all_info == {}:
            raise Exception(f"HoldInfo: redis: {self.target_stock}持仓信息不存在")
        # self.decoded_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in all_info.items()}
        # self.decoded_data = {k.decode('utf-8'): float(v.decode('utf-8')) for k, v in all_info.items()}
        for k, v in all_info.items():
            if k.decode('utf-8') in origin_str_list:
                self.decoded_data[k.decode('utf-8')] = v
            elif k.decode('utf-8') in origin_int_list:
                self.decoded_data[k.decode('utf-8')] = int(v)
            else:
                self.decoded_data[k.decode('utf-8')] = float(v)

    def reset_all(self):
        for key in origin_reset_list:
            self.remove(key)


def check_state(hold_stock, withdraw_order=False):
    LOGGING.info(f"检查更新状态: {hold_stock}")

    # 持仓信息
    hold_info = HoldInfo(hold_stock)

    # 获取编号
    execution_cycle = hold_info.get("execution_cycle")

    # ready情况下不用更新
    if execution_cycle == "ready":
        LOGGING.info("未生成执行编号,跳过同步")
        return

    # 查询未成交订单并取消
    sqlManager = TradeRecordManager(hold_stock, strategy_name=strategy_name)
    record_list_1 = sqlManager.filter_record(state="live")
    record_list_2 = sqlManager.filter_record(state="partially_filled")
    record_list = record_list_1 + record_list_2
    if not record_list:
        LOGGING.info("无live和part订单,跳过同步")
        return
    LOGGING.info(f"live和part订单数目: {len(record_list)}")

    time.sleep(3)  # 给予极端部分成交的情况充足的时间，因为部分成交也会触发这个函数
    geniusTrader = GeniusTrader(hold_stock, LOGGING=LOGGING)
    for client_order_id in record_list:
        # 查询执行结果
        result = geniusTrader.execution_result(client_order_id=client_order_id)
        LOGGING.info(f"订单详情: {result}")

        deal_data = result['data'][0]
        price_str = deal_data["fillPx"] if deal_data["ordType"] == "market" else deal_data["px"]
        state = deal_data["state"]
        price = float(price_str)
        amount = float(deal_data["sz"])
        value = amount * price
        fee = float(deal_data["fee"])
        side = deal_data["side"]
        if side == "buy":
            amount = amount + fee  # fee的值是负数，所以用+
            fee = -fee * price  # 买入时，手续费是按照标的物计算的
        if side == "sell":
            value = value + fee
            fee = -fee

        if state == "filled" or state == "partially_filled":  # 已成交,但是部分成交怎么办啊啊啊！！！！！
            fill_time = int(deal_data["fillTime"])
            sqlManager.update_trade_record(
                client_order_id,
                state=state,
                price=price,
                amount=amount,
                value=value,
                fill_time=datetime.fromtimestamp(fill_time / 1000.0),
                fee=fee,
            )
        if state == "canceled":
            sqlManager.update_trade_record(client_order_id, state="canceled")
        if withdraw_order and state == "live":
            geniusTrader.cancel_order(client_order_id=client_order_id)
            sqlManager.update_trade_record(client_order_id, state="canceled")

    long_position = sqlManager.get(execution_cycle, "long_position")
    sell_times = sqlManager.get(execution_cycle, "sell_times")

    # 查询未成交订单
    record_list = sqlManager.filter_record(state="live")
    new_info = {
        "pending_order": 1 if record_list else 0,
        "long_position": long_position,
        "sell_times": sell_times
    }
    LOGGING.info(new_info)

    # 如果此编号的状态是已完成，周期结束后，遇到close的情况下
    execution_state = sqlManager.get(execution_cycle, "execution_state")
    if execution_state == "completed":
        LOGGING.info("平仓已经完成，重置redis信息")
        hold_info.remove('add_price_list(ideal)')
        hold_info.remove('reduce_price_list(ideal)')
        hold_info.remove('close_price(ideal)')


        # 重置余额
        balance_delta = sqlManager.get(execution_cycle, "balance_delta")  # 虽然需要传编号，但是计算价差是用不着的
        init_balance = 100 + balance_delta

        new_info = {
           'execution_cycle': "ready",  # 重置编码
           'pending_order': 0,
           'tradeFlag': 'no-auth',  # 刚平完仓，不应该建仓
           'long_position': 0,
           'sell_times': 0,
           'build_price': 0,
           'init_balance': init_balance,
           'risk_rate': 0.0035,
           'max_long_position': 4,
           'max_sell_times': 3,
        }
    hold_info.pull_dict(new_info)


def show_account(result):
    """账户信息"""
    LOGGING.info("\n")

    data = result['data'][0]['balData']
    LOGGING.info("=====================资金用户===========================")
    # totalEq = round(float(totalEq), 2)
    # LOGGING.info(f'总资产: {totalEq} 美元')

    title = "账户更新"
    content = f"<font color=\"warning\">{title}</font>"
    for item in data:
        currency = item['ccy']
        cashBal = round(float(item['cashBal']), 8)

        # LOGGING.info(f"{currency}, 权益: {cashBal}, 现价: {eqUsd} USDT")
        LOGGING.info(f"{currency}, 权益: {cashBal}")
        content += f"\n>{currency}<font color=\"comment\">权益: {cashBal}</font>"

    custom_dict = {
        "msgtype": "markdown",
        "markdown": {
            "content": content
        }
    }

    if len(data) <= 2:
        res = send_wx_info(1, 1, custom=custom_dict, supreme_auth=True)
        LOGGING.info(res)


def prepare_login():
    timestamp = int(time.time())
    LOGGING.info(f"timestamp: {str(timestamp)}")
    sign = str(timestamp) + 'GET' + '/users/self/verify'
    total_params = bytes(sign, encoding='utf-8')
    signature = hmac.new(bytes(secret_key, encoding='utf-8'), total_params, digestmod=hashlib.sha256).digest()
    signature = base64.b64encode(signature)
    signature = str(signature, 'utf-8')
    LOGGING.info(f"signature = {signature}")

    account_msg = {
        "op": "login",
        "args": [
            {
                "apiKey": f'{api_key}',
                "passphrase": f'{passphrase}',
                "timestamp": f'{timestamp}',
                "sign": f'{signature}'
            }
        ]
    }

    return account_msg


origin_str_list = [
    "execution_cycle",
    "tradeFlag",
    "平仓价(-0.5N线)",
    "add_price_list(ideal)",
    "reduce_price_list(ideal)",
]

origin_int_list = [
    "max_long_position",
    "long_position",
    "max_sell_times",
    "sell_times",
]

origin_reset_list = [
    "add_price_list(ideal)",
    "reduce_price_list(ideal)",
]

strategy_name = "TURTLE"



if __name__ == '__main__':
    hold_stock = "FLOKI-USDT"
    hold_info = HoldInfo(hold_stock)
    execution_cycle = hold_info.get("execution_cycle")
    print(execution_cycle)
    # long_position = sqlManager.get(execution_cycle, "long_position")
    # print(long_position)
    check_state(hold_info)

