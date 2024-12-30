import json
import socket
import time

import redis
from datetime import datetime, timezone, timedelta

import asyncio
import websockets

from MsgSender.wx_msg import send_wx_info
from MsgSender.feishu_msg import send_feishu_info
from utils.url_center import redis_url
from module.trade_records import TradeRecordManager
from module.trade_assistant import TradeAssistant
from monitor.account_monitor import check_state
from monitor.account_monitor import HoldInfo
from monitor.account_monitor import prepare_login

import sys

# 第一个参数是脚本名称，后续的是传入的参数
if len(sys.argv) > 1:
    target_stock = sys.argv[1]  # 这里会得到 '123'
    print(f"The argument target_stock is: {target_stock}")
else:
    print("Error: No arguments were passed. Please provide an target_stock and try again!")
    sys.exit(1)  # 使用非零状态码表示异常退出

sort_name = target_stock.split('-')[0]

import logging.config
from utils.logging_config import Logging_dict

logging.config.dictConfig(Logging_dict)
LOGGING = logging.getLogger(f"quantVole-{sort_name}")
# LOGGING = logging.getLogger(f"quantVole")


# target_stock = "LUNC-USDT"
# target_stock = "BTC-USDT"
# target_stock = "ETH-USDT"
# target_stock = "FLOKI-USDT"
# target_stock = "OMI-USDT"
# target_stock = "DOGE-USDT"
# target_stock = "PEPE-USDT"

# 订阅账户频道的消息
subscribe_msg = {
    "op": "subscribe",
    "args": [
        {
            # "channel": "price-limit",
            "channel": "trades",
            "instId": target_stock
        }
    ]
}

price_dict = {}

redis_okx = redis.Redis.from_url(redis_url)
last_read_time = redis_okx.hget(f"common_index:{target_stock}", 'last_read_time')
DayStamp = last_read_time.decode() if last_read_time is not None else None

# 持仓信息
hold_info = HoldInfo(target_stock, LOGGING=LOGGING)
execution_cycle = hold_info.get("execution_cycle")

# 交易助手
agent = TradeAssistant('TURTLE', target_stock, trade_type="actual", LOGGING=LOGGING)
# agent = TradeAssistant('TURTLE', target_stock, trade_type="simulate")


# 数据库记录
sqlManager = TradeRecordManager(target_stock, "TURTLE")

auth_time = 0


def trade_auth(side):
    global auth_time
    auth_time += 1
    tradeFlag = hold_info.newest("tradeFlag")

    record_list_1 = sqlManager.filter_record(state="live")
    record_list_2 = sqlManager.filter_record(state="partially_filled")
    record_list = record_list_1 + record_list_2
    if record_list:
        if auth_time == 1:
            LOGGING.warning(f"<{side}>: no access to trade,数据库中仍然有挂单未同步")
        return False

    if tradeFlag == "all-auth":
        LOGGING.info(f"<{side}>: trade approved")
        return True

    if tradeFlag == "buy-only" and side == "buy":
        LOGGING.info(f"<{side}>: trade approved")
        return True

    if tradeFlag == "sell-only" and side == "sell":
        LOGGING.info(f"<{side}>: trade approved")
        return True

    if tradeFlag == "no-auth":
        if auth_time == 1:
            LOGGING.warning(f"<{side}>: no access to trade")
        return False

    if auth_time == 1:
        LOGGING.warning(f"<{side}>: no access to trade")
    return False


def compute_amount(operation, target_market_price):
    amount = round(hold_info.get("risk_rate") * hold_info.get("init_balance") / hold_info.get("ATR"), 5)
    # max_rate = 0.31 if operation == "build" else 0.231
    max_rate, min_rate = 0.31, 0.231
    # min_rate = 0.24 if operation == "build" else 0.171
    expect_max_cost = hold_info.get("init_balance") * max_rate
    expect_min_cost = hold_info.get("init_balance") * min_rate
    now_cost = amount * target_market_price
    if now_cost > expect_max_cost:
        LOGGING.info("超预算(减少数量)")
        amount = expect_max_cost / target_market_price
    if expect_min_cost > now_cost:
        LOGGING.info("未达预算(增加数量)")
        amount = expect_min_cost / target_market_price

    return amount


def compute_target_price(ATR, up_Dochian_price, down_Dochian_price):
    LOGGING.info("计算目标价")
    global price_dict
    print(price_dict)

    # 计算目标价格
    # long_position = hold_info.newest("long_position")
    # build_price = hold_info.newest("build_price")
    # execution_cycle = hold_info.get("execution_cycle")
    long_position = sqlManager.get(execution_cycle, "long_position")
    build_price = sqlManager.get(execution_cycle, "build_price")
    total_max_value = sqlManager.get(execution_cycle, "total_max_value")
    total_max_amount = sqlManager.get(execution_cycle, "total_max_amount")
    hold_average_price = total_max_value / total_max_amount if total_max_amount > 0 else build_price

    # stop_loss_price = round(build_price - 0.5 * ATR, 10)
    stop_loss_price = round(hold_average_price - 0.5 * ATR, 10)

    if stop_loss_price > down_Dochian_price:
        close_price = stop_loss_price
        close_type = "-0.5N线"
    else:
        close_price = down_Dochian_price
        close_type = "唐奇安下线"

    price_dict_2_redis = {
        'ATR': ATR,
        '平仓价(-0.5N线)': '未建仓' if long_position == 0 else stop_loss_price,
    }

    price_dict = {
        'ATR': ATR,
        'close_price(ideal)': close_price,
        'close_type': close_type,
    }
    print(price_dict)

    # long_position = hold_info.newest("long_position")

    if long_position == 0:
        price_dict_2_redis['build_price(ideal)'] = up_Dochian_price
        price_dict['build_price(ideal)'] = up_Dochian_price

    if long_position > 0:
        hold_info.remove('build_price(ideal)')
        add_price_list = []
        reduce_price_list = []

        for i in range(1, hold_info.get("max_long_position")):
            target_market_price = round(build_price + i * 0.5 * ATR, 10)
            add_price_list.append(target_market_price)

        for i in range(0, hold_info.get("max_sell_times")):
            target_market_price = round(build_price + (0.5 * i + 2) * ATR, 10)
            reduce_price_list.append(target_market_price)

        price_dict_2_redis['close_price(ideal)'] = close_price
        price_dict_2_redis['add_price_list(ideal)'] = str(add_price_list)
        price_dict_2_redis['reduce_price_list(ideal)'] = str(reduce_price_list)
        price_dict['close_price(ideal)'] = close_price
        price_dict['close_type'] = close_type
        price_dict['add_price_list(ideal)'] = add_price_list
        price_dict['reduce_price_list(ideal)'] = reduce_price_list
        print(add_price_list)
        print(price_dict)

    hold_info.pull_dict(price_dict_2_redis)


def notice_change(long_position, sell_times):
    if long_position != hold_info.get("long_position") or sell_times != hold_info.get("sell_times"):
        LOGGING.info("持仓发生变化,立即拉取redis")
        load_index_and_compute_price(target_stock)


def load_index_and_compute_price(target_stock):
    # 获取单个字段的值
    name = redis_okx.hget(f"common_index:{target_stock}", 'update_time')
    if name is None:
        raise Exception(f"load_reference_index: redis: {target_stock}股票参数不存在")

    name = name.decode()
    LOGGING.info(f"开始更新参数, 上次更新时间: {name}")

    # 获取整个哈希表的所有字段和值
    all_info = redis_okx.hgetall(f"common_index:{target_stock}")

    # 解码每个键和值
    decoded_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in all_info.items()}
    # LOGGING.info(decoded_data)

    up_Dochian_price = float(decoded_data['history_max_price'])
    down_Dochian_price = float(decoded_data['history_min_price'])
    ATR = float(decoded_data['ATR'])

    LOGGING.info(ATR)
    LOGGING.info(up_Dochian_price)
    LOGGING.info(down_Dochian_price)

    compute_target_price(ATR, up_Dochian_price, down_Dochian_price)


def timed_task():
    bj_tz = timezone(timedelta(hours=8))
    now_bj = datetime.now().astimezone(bj_tz)
    # today = now_bj.day  # 当前月份的第几天
    hour_of_day = now_bj.hour  # 第几时
    minute = now_bj.minute  # 第几分

    if hour_of_day in [0, 4, 8, 12, 16, 20] and minute == 2:
        # if hour_of_day in [0, 4, 8, 12, 16, 20, 13] and minute == 17:
        global DayStamp
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        if DayStamp is not None and current_time == DayStamp:
            return

        # # 发微信
        # res = send_wx_info("读取最新策略参数", f"{current_time}", supreme_auth=True)
        # LOGGING.info(res)

        load_index_and_compute_price(target_stock)
        DayStamp = current_time
        redis_okx.hset(f"common_index:{target_stock}", 'last_read_time', current_time)
        LOGGING.info(f"到点了 :{current_time} ")

        # 取消未成交的挂单
        # check_state(target_stock, sqlManager, hold_info, geniusTrader, withdraw_order=True)
        # check_state(target_stock, withdraw_order=True)
        check_state(target_stock, withdraw_order=False, LOGGING=LOGGING)

        # 开放交易权限
        hold_info.pull("tradeFlag", "all-auth")  # 同步新编号

        LOGGING.info(f"持续跟踪价格中...")


from utils.url_center import redis_url_fastest

redis_fastest = redis.Redis.from_url(redis_url_fastest)
origin_str_list = [
    "execution_cycle",
    "update_time(24时制)",
]

origin_int_list = [
    "update_time",
    "long_position",
    "max_sell_times",
    "sell_times",
]


def get_real_time_info():
    timestamp_seconds = time.time()
    timestamp_ms = int(timestamp_seconds * 1000)  # 转换为毫秒
    all_info = redis_fastest.hgetall(f"real_time_index:{target_stock}")
    decoded_data = {}
    for k, v in all_info.items():
        if k.decode('utf-8') in origin_str_list:
            decoded_data[k.decode('utf-8')] = v.decode('utf-8')
        elif k.decode('utf-8') in origin_int_list:
            decoded_data[k.decode('utf-8')] = int(v.decode('utf-8'))
        else:
            decoded_data[k.decode('utf-8')] = float(v.decode('utf-8'))
    update_time = decoded_data["update_time"]
    delta_time = timestamp_ms - update_time
    print(update_time, timestamp_ms)
    print(delta_time)
    print()
    if delta_time > 6000*5:
        raise Exception(f"价格数据已经严重滞后: {delta_time} ms")
    # print(decoded_data)
    return decoded_data


def circle():
    global execution_cycle, price_dict
    while True:
        reconnect_attempts = 0

        try:
            # 计算目标价
            load_index_and_compute_price(target_stock)

            while True:
                # 更新策略参数
                timed_task()

                # 挂单数大于零直接跳过
                pending_order = hold_info.newest("pending_order")
                if pending_order > 0:
                    # print(12345678)
                    continue

                # 获取最新报价
                data_dict = get_real_time_info()

                now_price = data_dict["now_price"]
                agent.now_price = now_price
                long_position = hold_info.newest("long_position")
                sell_times = hold_info.newest("sell_times")

                # 更新策略参数
                notice_change(long_position, sell_times)

                # 空仓时
                if long_position == 0:
                    # print(111)
                    # 计算目标价格
                    target_market_price = price_dict['build_price(ideal)']
                    if target_market_price < now_price:
                        if not trade_auth("buy"):
                            continue
                        # 生成新编号
                        execution_cycle = sqlManager.generate_execution_cycle()
                        # 计算目标数量
                        amount = compute_amount("build", target_market_price)
                        # 买入
                        agent.buy("build", execution_cycle, target_market_price, amount, remark="建仓")

                        new_info = {
                            "pending_order": 1,
                            # "build_price": target_market_price,
                            "execution_cycle": execution_cycle,  # 同步新编号
                            "tradeFlag": "buy-only"
                        }
                        hold_info.pull_dict(new_info)
                        continue

                # 未满仓,加仓
                if 0 < long_position < hold_info.get("max_long_position"):
                    # print(222)
                    # print(price_dict)
                    # print(price_dict['add_price_list(ideal)'])
                    target_market_price = price_dict['add_price_list(ideal)'][long_position - 1]
                    if target_market_price < now_price:
                        if not trade_auth("buy"):
                            continue
                        # 计算目标数量
                        amount = compute_amount("add", target_market_price)
                        # 买入
                        agent.buy("add", execution_cycle, target_market_price, amount, remark="加仓")

                        hold_info.pull("pending_order", 1)
                        continue

                # 卖出 ============= SELL =========SELL===========SELL===================== SELL

                # 满仓情况,逐步卖出
                # print(333)
                if long_position == hold_info.get("max_long_position") and sell_times <= hold_info.get(
                        "max_sell_times"):
                    target_market_price = price_dict['reduce_price_list(ideal)'][sell_times]
                    if now_price < target_market_price:
                        if not trade_auth("sell"):
                            continue
                        msg = f"减仓(+{0.5 * sell_times + 2}N线, 分批止盈)"

                        # 卖出
                        ratio = 0.3 if sell_times <= 1 else 0.2
                        agent.sell(execution_cycle, target_market_price, ratio, remark=msg)
                        hold_info.pull("pending_order", 1)
                        # 判断是否为全卖空，全卖完还要记得"tradeFlag": "no-auth"
                        continue

                # 止损
                if long_position > 0:
                    # print(666)
                    close_price = price_dict["close_price(ideal)"]
                    if now_price < close_price:
                        if not trade_auth("sell"):
                            continue
                        msg = price_dict["close_type"]
                        ratio = 1
                        agent.sell(execution_cycle, close_price, ratio, remark=msg)

                        new_info = {
                            "pending_order": 1,
                            "tradeFlag": "no-auth"
                        }
                        time.sleep(10)
                        hold_info.pull_dict(new_info)

        # 重新尝试连接，使用指数退避策略,针对于“远程计算机拒绝网络连接”错误
        except socket.error as e:
            reconnect_attempts += 1
            wait_time = min(2 ** reconnect_attempts, 60)  # 最大等待时间为60秒
            LOGGING.info(f"Connection closed: {e}\n Reconnecting in {wait_time} seconds...")
            time.sleep(wait_time)

        except Exception as e:
            LOGGING.info(f'连接断开，不重新连接，请检查……其他: {e}')
            if "sbsb" in str(e):
                LOGGING.info("Timeout , and reconnecting")
                time.sleep(10)
                continue
            if "pymysql.err.OperationalError" in str(e):  # 应对mysql连接断开
                LOGGING.info("Timeout , and reconnecting")
                time.sleep(10)
                continue
            break


if __name__ == '__main__':
    # 开始执行
    circle()
