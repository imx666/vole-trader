import time
import redis
from datetime import datetime, timezone, timedelta

from MsgSender.wx_msg import send_wx_info
from MsgSender.feishu_msg import send_feishu_info
from utils.url_center import redis_url
from module.trade_records import TradeRecordManager
from module.trade_assistant import TradeAssistant
from module.trade_assistant import get_real_time_info, slip, load_index
from monitor.account_monitor import check_state
from monitor.account_monitor import HoldInfo

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

# 相关参数
redis_okx = redis.Redis.from_url(redis_url)
last_read_time = redis_okx.hget(f"common_index:{target_stock}", 'last_read_time')
DayStamp = last_read_time.decode() if last_read_time is not None else None

# 持仓信息
hold_info = HoldInfo(target_stock, LOGGING=LOGGING)
execution_cycle = hold_info.get("execution_cycle")

# 交易助手
agent = TradeAssistant('TURTLE', target_stock, trade_type="actual", LOGGING=LOGGING)

# # 数据库记录
# sqlManager = TradeRecordManager(target_stock, "TURTLE")

auth_time = 0
price_dict = {}


def trade_auth(side):
    global auth_time
    auth_time += 1
    tradeFlag = hold_info.newest("tradeFlag")

    sqlManager = TradeRecordManager(target_stock, "TURTLE")

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
    amount = round(hold_info.get("<risk_rate>") * hold_info.get("<init_balance>") / hold_info.get("ATR"), 8)
    if operation == "build":
        max_rate, min_rate = 0.331, 0.251
    else:
        max_rate, min_rate = 0.311, 0.231

    expect_max_cost = hold_info.get("<init_balance>") * max_rate
    expect_min_cost = hold_info.get("<init_balance>") * min_rate
    now_cost = amount * target_market_price
    if now_cost > expect_max_cost:
        LOGGING.info("超预算(减少数量)")
        amount = expect_max_cost / target_market_price
    if expect_min_cost > now_cost:
        LOGGING.info("未达预算(增加数量)")
        amount = expect_min_cost / target_market_price

    return amount


# def compute_target_price(ATR, up_Dochian_price, down_Dochian_price):
#     global price_dict
#     LOGGING.info("计算目标价")
#     sqlManager = TradeRecordManager(target_stock, "TURTLE")
#
#     execution_cycle = hold_info.newest("execution_cycle")
#     long_position = hold_info.newest("long_position")
#     build_price = sqlManager.get(execution_cycle, "build_price")
#     total_max_value = sqlManager.get(execution_cycle, "total_max_value")
#     total_max_amount = sqlManager.get(execution_cycle, "total_max_amount")
#     hold_average_price = total_max_value / total_max_amount if total_max_amount > 0 else build_price
#
#     LOGGING.info(f"多头持仓: {long_position}")
#     if long_position > 0:
#         LOGGING.info(f"建仓价: {build_price}")
#         LOGGING.info(f"持仓均价: {hold_average_price}")
#
#     # stop_loss_price = round(build_price - 0.5 * ATR, 10)
#     stop_loss_price = round(hold_average_price - 0.5 * ATR, 10)
#
#     if stop_loss_price > down_Dochian_price:
#         close_price = stop_loss_price
#         close_type = "-0.5N线"
#     else:
#         close_price = down_Dochian_price
#         close_type = "唐奇安下线"
#
#     price_dict_2_redis = {
#         'ATR': ATR,
#         '平仓价(-0.5N线)': '未建仓' if long_position == 0 else stop_loss_price,
#     }
#
#     price_dict = {
#         'ATR': ATR,
#         'close_price(ideal)': close_price,
#         'close_type': close_type,
#     }
#
#     if long_position == 0:
#         price_dict_2_redis['build_price(ideal)'] = up_Dochian_price
#         price_dict['build_price(ideal)'] = up_Dochian_price
#         LOGGING.info(f"理想建仓价: {up_Dochian_price}")
#
#     if long_position > 0:
#         add_price_list = []
#         reduce_price_list = []
#
#         for i in range(1, hold_info.get("<max_long_position>")):
#             target_market_price = round(build_price + i * 0.5 * ATR, 10)
#             add_price_list.append(target_market_price)
#
#         for i in range(0, hold_info.get("<max_sell_times>")):
#             target_market_price = round(build_price + (0.5 * i + 2) * ATR, 10)
#             reduce_price_list.append(target_market_price)
#
#         price_dict_2_redis['close_price(ideal)'] = close_price
#         price_dict_2_redis['add_price_list(ideal)'] = str(add_price_list)
#         price_dict_2_redis['reduce_price_list(ideal)'] = str(reduce_price_list)
#         price_dict['close_price(ideal)'] = close_price
#         price_dict['close_type'] = close_type
#         price_dict['add_price_list(ideal)'] = add_price_list
#         price_dict['reduce_price_list(ideal)'] = reduce_price_list
#
#     LOGGING.info(price_dict)
#     hold_info.pull_dict(price_dict_2_redis)


def compute_sb_price(target_stock):
    up_Dochian_price, down_Dochian_price, ATR, last_time = load_index(target_stock)
    LOGGING.info(f"开始更新参数, 上次更新时间: {last_time}")
    LOGGING.info(ATR)
    LOGGING.info(up_Dochian_price)
    LOGGING.info(down_Dochian_price)

    global price_dict
    LOGGING.info("计算目标价")
    sqlManager = TradeRecordManager(target_stock, "TURTLE")

    execution_cycle = hold_info.newest("execution_cycle")
    long_position = hold_info.newest("long_position")
    build_price = sqlManager.get(execution_cycle, "build_price")
    total_max_value = sqlManager.get(execution_cycle, "total_max_value")
    total_max_amount = sqlManager.get(execution_cycle, "total_max_amount")
    hold_average_price = total_max_value / total_max_amount if total_max_amount > 0 else build_price

    LOGGING.info(f"多头持仓: {long_position}")
    if long_position > 0:
        LOGGING.info(f"建仓价: {build_price}")
        LOGGING.info(f"持仓均价: {hold_average_price}")

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

    if long_position == 0:
        price_dict_2_redis['build_price(ideal)'] = up_Dochian_price
        price_dict['build_price(ideal)'] = up_Dochian_price
        LOGGING.info(f"理想建仓价: {up_Dochian_price}")

    if long_position > 0:
        add_price_list = []
        reduce_price_list = []

        for i in range(1, hold_info.get("<max_long_position>")):
            target_market_price = round(build_price + i * 0.5 * ATR, 10)
            add_price_list.append(target_market_price)

        for i in range(0, hold_info.get("<max_sell_times>")):
            target_market_price = round(build_price + (0.5 * i + 2) * ATR, 10)
            reduce_price_list.append(target_market_price)

        price_dict_2_redis['close_price(ideal)'] = close_price
        price_dict_2_redis['add_price_list(ideal)'] = str(add_price_list)
        price_dict_2_redis['reduce_price_list(ideal)'] = str(reduce_price_list)
        price_dict['close_price(ideal)'] = close_price
        price_dict['close_type'] = close_type
        price_dict['add_price_list(ideal)'] = add_price_list
        price_dict['reduce_price_list(ideal)'] = reduce_price_list

    LOGGING.info(price_dict)
    hold_info.pull_dict(price_dict_2_redis)

def notice_change(long_position, sell_times):
    if long_position != hold_info.get("long_position") or sell_times != hold_info.get("sell_times"):
        LOGGING.info("持仓发生变化,立即拉取redis")
        # load_index_and_compute_price(target_stock)
        compute_sb_price(target_stock)



# def load_index_and_compute_price(target_stock):
#     # 获取单个字段的值
#     redis_okx = redis.Redis.from_url(redis_url)
#     name = redis_okx.hget(f"common_index:{target_stock}", 'update_time')
#     if name is None:
#         raise Exception(f"load_reference_index: redis: {target_stock}股票参数不存在")
#
#     name = name.decode()
#     LOGGING.info(f"开始更新参数, 上次更新时间: {name}")
#
#     # 获取整个哈希表的所有字段和值
#     all_info = redis_okx.hgetall(f"common_index:{target_stock}")
#
#     # 解码每个键和值
#     decoded_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in all_info.items()}
#     # LOGGING.info(decoded_data)
#
#     up_Dochian_price = float(decoded_data['history_max_price'])
#     down_Dochian_price = float(decoded_data['history_min_price'])
#     ATR = float(decoded_data['ATR'])
#
#     LOGGING.info(ATR)
#     LOGGING.info(up_Dochian_price)
#     LOGGING.info(down_Dochian_price)
#
#     compute_target_price(ATR, up_Dochian_price, down_Dochian_price)


def timed_task():
    bj_tz = timezone(timedelta(hours=8))
    now_bj = datetime.now().astimezone(bj_tz)
    # today = now_bj.day  # 当前月份的第几天
    hour_of_day = now_bj.hour  # 第几时
    minute = now_bj.minute  # 第几分

    if hour_of_day in [0, 4, 8, 12, 16, 20] and minute == 2:
        # if hour_of_day in [1, 4, 8, 12, 16, 20, 13] and minute == 1:
        global DayStamp, auth_time
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        if DayStamp is not None and current_time == DayStamp:
            return

        DayStamp = current_time
        redis_okx = redis.Redis.from_url(redis_url)
        redis_okx.hset(f"common_index:{target_stock}", 'last_read_time', current_time)
        LOGGING.info(f"到点了: {current_time} ")
        auth_time = 0

        # load_index_and_compute_price(target_stock)
        compute_sb_price(target_stock)

        # 取消未成交的挂单
        check_state(target_stock, withdraw_order=True, LOGGING=LOGGING)

        # 开放交易权限
        hold_info.pull("tradeFlag", "all-auth")

        LOGGING.info(f"持续跟踪价格中...")


def circle():
    global execution_cycle, price_dict
    # 计算目标价
    # load_index_and_compute_price(target_stock)
    compute_sb_price(target_stock)

    try:
        while True:
            # 更新策略参数
            timed_task()

            # 挂单数大于零直接跳过
            pending_order = hold_info.newest("pending_order")
            if pending_order > 0:
                time.sleep(1)
                continue

            # 获取最新报价
            data_dict = get_real_time_info(target_stock, LOGGING)
            if data_dict is None:
                time.sleep(0.01)
                continue

            now_price = data_dict["now_price"]
            agent.now_price = now_price
            long_position = hold_info.newest("long_position")
            sell_times = hold_info.newest("sell_times")

            # 更新策略参数
            notice_change(long_position, sell_times)

            # 空仓时
            if long_position == 0:
                # print(111)
                target_market_price = price_dict['build_price(ideal)']
                if target_market_price < now_price - slip(now_price):
                    if not trade_auth("buy"):
                        continue
                    # 生成新编号
                    sqlManager = TradeRecordManager(target_stock, "TURTLE")
                    execution_cycle = sqlManager.generate_execution_cycle()

                    # 买入
                    amount = compute_amount("build", target_market_price)
                    agent.buy("build", execution_cycle, target_market_price, amount, remark="建仓")
                    new_info = {
                        "pending_order": 1,
                        "execution_cycle": execution_cycle,  # 同步新编号
                        "tradeFlag": "buy-only"
                    }
                    hold_info.pull_dict(new_info)
                    continue

            # 未满仓,加仓
            if 0 < long_position < hold_info.get("<max_long_position>"):
                # print(222)
                # print(price_dict)
                target_market_price = price_dict['add_price_list(ideal)'][long_position - 1]
                if target_market_price < now_price - slip(now_price):
                    if not trade_auth("buy"):
                        continue
                    # 买入
                    amount = compute_amount("add", target_market_price)
                    agent.buy("add", execution_cycle, target_market_price, amount, remark="加仓")
                    hold_info.pull("pending_order", 1)
                    continue

            # 卖出 ============= SELL =========SELL===========SELL===================== SELL

            # 满仓情况,逐步卖出
            if long_position == hold_info.get("<max_long_position>") and sell_times < hold_info.get(
                    "<max_sell_times>"):
                # print(333)
                target_market_price = price_dict['reduce_price_list(ideal)'][sell_times]
                if now_price < target_market_price:
                    if not trade_auth("sell"):
                        continue

                    # 卖出
                    msg = f"减仓(+{0.5 * sell_times + 2}N线, 分批止盈)"
                    ratio = 0.3 if sell_times <= 1 else 0.2
                    operation = "reduce"
                    if sell_times == hold_info.get("<max_sell_times>") - 1:  # 不能是完全的多头满的状态来
                        ratio = 1
                        operation = "close"
                    agent.sell(operation, execution_cycle, target_market_price, ratio, remark=msg)
                    new_info = {
                        "pending_order": 1,
                        "tradeFlag": "sell-only"  # 不能给no-auth，任何时候都得保证最后的平仓可以顺利进行
                    }
                    hold_info.pull_dict(new_info)
                    # 判断是否为全卖空，全卖完还要记得"tradeFlag": "no-auth"
                    continue

            # 止损
            if long_position > 0:
                # print(666)
                close_price = price_dict["close_price(ideal)"]
                if now_price < close_price:
                    if not trade_auth("sell"):
                        continue

                    # 卖出
                    msg = price_dict["close_type"]
                    ratio = 1
                    agent.sell("close", execution_cycle, close_price, ratio, remark=msg)
                    new_info = {
                        "pending_order": 1,
                        "tradeFlag": "no-auth"
                    }
                    hold_info.pull_dict(new_info)
    except Exception as e:
        LOGGING.error(e)


if __name__ == '__main__':
    # 开始执行
    circle()
