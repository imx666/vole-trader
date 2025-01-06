import time
import redis
from datetime import datetime, timezone, timedelta

from module.super_okx import GeniusTrader
from module.trade_records import TradeRecordManager

from utils.url_center import redis_url
from utils.url_center import redis_url_fastest
from utils.LOGGING_2 import LOGGING_2
from monitor.account_monitor import HoldInfo, check_state

hold_info = HoldInfo()
redis_fastest = redis.Redis.from_url(redis_url_fastest)

# 交易api
geniusTrader = GeniusTrader()

# 数据库记录
sqlManager = TradeRecordManager()

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

latest_update_time = time.time()


class TradeAssistant:
    def __init__(self, strategy_name, target_stock, trade_type, LOGGING=None):
        global geniusTrader, sqlManager
        sqlManager.target_stock = target_stock
        sqlManager.strategy = strategy_name
        geniusTrader.target_stock = target_stock

        self.geniusTrader = geniusTrader
        self.sqlManager = sqlManager
        self.trade_type = trade_type
        self.buyLmt = None
        self.sellLmt = None
        self.now_price = None
        self.msg = None

        if LOGGING is None:
            self.LOGGING = LOGGING_2
        else:
            self.LOGGING = LOGGING
            geniusTrader.LOGGING = LOGGING

    def show_moment(self, target_market_price, amount):
        if self.msg is not None:
            self.LOGGING.info(f"remark: {self.msg}")
        self.LOGGING.info(f"现价: {self.now_price}")
        self.LOGGING.info(f"目标价: {target_market_price}, 数量: {amount}")
        # self.LOGGING.info(f"买限: {self.buyLmt}, 卖限: {self.sellLmt}")

    def sell(self, operation, execution_cycle, target_market_price, ratio, remark=None, order_type="limit"):
        total_max_amount = self.sqlManager.get(execution_cycle, "total_max_amount")
        target_amount = total_max_amount * ratio
        rest_amount = self.sqlManager.get(execution_cycle, "rest_amount")
        amount = rest_amount if rest_amount < target_amount else target_amount
        # operation = "close" if rest_amount <= target_amount else "reduce"

        if self.trade_type == "simulate":
            self.simulate(execution_cycle, operation, target_market_price, amount)
            return

        self.msg = operation if remark is None else remark
        self.show_moment(target_market_price, amount)
        client_order_id, timestamp_ms = self.geniusTrader.sell_order(amount=amount, price=target_market_price,
                                                                     order_type=order_type)

        # 添加一条新记录
        self.sqlManager.add_trade_record(
            create_time=datetime.fromtimestamp(timestamp_ms / 1000.0),
            execution_cycle=execution_cycle,
            operation=operation,
            client_order_id=client_order_id,
            price=target_market_price,
            amount=amount,
            value=round(target_market_price * amount, 3),
            remark=remark if remark is not None else None,
        )

    def buy(self, operation, execution_cycle, target_market_price, amount, remark=None, order_type="limit"):
        if self.trade_type == "simulate":
            self.simulate(execution_cycle, operation, target_market_price, amount)
            return

        self.msg = operation if remark is None else remark
        self.show_moment(target_market_price, amount)
        client_order_id, timestamp_ms = self.geniusTrader.buy_order(amount=amount, price=target_market_price,
                                                                    order_type=order_type)

        # 添加一条新记录
        self.sqlManager.add_trade_record(
            create_time=datetime.fromtimestamp(timestamp_ms / 1000.0),
            execution_cycle=execution_cycle,
            operation=operation,
            client_order_id=client_order_id,
            price=target_market_price,
            amount=amount,
            value=round(target_market_price * amount, 3),
            remark=remark if remark is not None else None,
        )

    def simulate(self, execution_cycle, operation, target_market_price, amount):
        timestamp_seconds = time.time()
        timestamp_ms = int(timestamp_seconds * 1000)  # 转换为毫秒
        target_stock = self.geniusTrader.target_stock
        sort_name = target_stock.split("-")[0]
        client_order_id = f"{sort_name}{timestamp_ms}"
        # 添加一条新记录
        self.sqlManager.add_trade_record(
            create_time=datetime.fromtimestamp(timestamp_ms / 1000.0),
            execution_cycle=execution_cycle,
            operation=operation,
            client_order_id=client_order_id,
            price=target_market_price,
            amount=amount,
            value=round(target_market_price * amount, 3),
        )


def get_real_time_info(target_stock):
    LOGGING = hold_info.LOGGING
    global latest_update_time
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
    if update_time == latest_update_time:
        return None
    else:
        latest_update_time = update_time
        # LOGGING.info(f"{update_time}, {timestamp_ms}")
        # LOGGING.info(delta_time)
        # LOGGING.info(decoded_data["now_price"])
        # LOGGING.info('\n')

    if delta_time > 1000 * 60 * 15:  # 15min
        raise Exception(f"价格数据已经严重滞后: {delta_time / 1000} s")

    return decoded_data


def slip(now_price):
    if now_price >= 10000:
        delta = 1
    elif now_price >= 1000:
        delta = 0.3
    elif now_price >= 100:
        delta = 0.1
    elif now_price >= 1:
        delta = 0.01
    else:
        delta = now_price / 1000

        str_value = f"{delta:.10f}"  # 保留足够的小数位，避免浮点数精度问题
        # 获取小数点的位置
        decimal_index = str_value.find('.')

        # 计算前导零的个数
        if decimal_index != -1:
            # 计算小数部分的长度
            decimal_part = str_value[decimal_index + 1:]  # 获取小数部分
            leading_zeros = len(decimal_part) - len(decimal_part.lstrip('0'))  # 计算前导零
            delta = round(delta, leading_zeros + 1)
            print(leading_zeros, delta)

    return delta


def load_index(target_stock):
    # 获取单个字段的值
    redis_okx = redis.Redis.from_url(redis_url)
    name = redis_okx.hget(f"common_index:{target_stock}", 'update_time')
    if name is None:
        raise Exception(f"load_reference_index: redis: {target_stock}股票参数不存在")

    last_time = name.decode()

    # 获取整个哈希表的所有字段和值
    all_info = redis_okx.hgetall(f"common_index:{target_stock}")

    # 解码每个键和值
    decoded_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in all_info.items()}
    # LOGGING.info(decoded_data)

    up_Dochian_price = float(decoded_data['history_max_price'])
    down_Dochian_price = float(decoded_data['history_min_price'])
    ATR = float(decoded_data['ATR'])

    return up_Dochian_price, down_Dochian_price, ATR, last_time


def compute_amount(operation, target_market_price):
    LOGGING = hold_info.LOGGING
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


def compute_sb_price(target_stock):
    LOGGING = hold_info.LOGGING

    up_Dochian_price, down_Dochian_price, ATR, last_time = load_index(target_stock)
    LOGGING.info(f"开始更新参数, 上次更新时间: {last_time}")
    LOGGING.info(ATR)
    LOGGING.info(up_Dochian_price)
    LOGGING.info(down_Dochian_price)

    LOGGING.info("计算目标价")
    long_position = hold_info.newest("long_position")
    execution_cycle = hold_info.newest("execution_cycle")

    # sqlManager = TradeRecordManager(target_stock, "TURTLE")
    build_price = sqlManager.get(execution_cycle, "build_price")
    total_max_value = sqlManager.get(execution_cycle, "total_max_value")
    total_max_amount = sqlManager.get(execution_cycle, "total_max_amount")
    hold_average_price = total_max_value / total_max_amount if total_max_amount > 0 else build_price

    LOGGING.info(f"多头持仓: {long_position}")
    if long_position > 0:
        LOGGING.info(f"建仓价: {build_price}")
        LOGGING.info(f"持仓均价: {hold_average_price}")

    # 成本平仓价
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
        'close_price(ideal)': close_price,
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

        price_dict_2_redis['add_price_list(ideal)'] = str(add_price_list)
        price_dict_2_redis['reduce_price_list(ideal)'] = str(reduce_price_list)
        price_dict['add_price_list(ideal)'] = add_price_list
        price_dict['reduce_price_list(ideal)'] = reduce_price_list

    hold_info.pull_dict(price_dict_2_redis)
    LOGGING.info(price_dict)
    hold_info.price_dict = price_dict
    LOGGING.info(f"持续跟踪价格中...")


trade_auth_warning = None


# def trade_auth(side=None, reset=False):
#     global trade_auth_warning
#
#     # 重置输出标志位
#     if reset:
#         trade_auth_warning = None
#         return
#
#     LOGGING = hold_info.LOGGING
#
#     tradeFlag = hold_info.newest("tradeFlag")
#
#     # 虽然redis中有pending order这一参数，但是极端情况是redis还未来得及更新，然后就重复挂单
#     record_list_1 = sqlManager.filter_record(state="live")
#     record_list_2 = sqlManager.filter_record(state="partially_filled")
#     record_list = record_list_1 + record_list_2
#     if record_list:
#         msg = f"<{side}>: no access to trade, 数据库中仍然有挂单未同步"
#         if msg != trade_auth_warning:
#             LOGGING.warning(msg)
#             trade_auth_warning = msg
#         return False
#
#     if tradeFlag != "build" and side == "close":
#         LOGGING.info(f"<{side}>: trade approved")
#         return True
#
#     if tradeFlag == "all-auth":
#         LOGGING.info(f"<{side}>: trade approved")
#         return True
#
#     if tradeFlag == "buy-only" and side == "buy":
#         LOGGING.info(f"<{side}>: trade approved")
#         return True
#
#     if tradeFlag == "sell-only" and side == "sell":
#         LOGGING.info(f"<{side}>: trade approved")
#         return True
#
#     if tradeFlag == "no-auth":
#         msg = f"<{side}>: no access to trade ({tradeFlag})"
#         if msg != trade_auth_warning:
#             LOGGING.warning(msg)
#             trade_auth_warning = msg
#         return False
#
#     msg = f"<{side}>: no access to trade ({tradeFlag})"
#     if msg != trade_auth_warning:
#         LOGGING.warning(msg)
#         trade_auth_warning = msg
#     return False


def trade_auth(side=None, reset=False):
    """
    检查是否有权限进行交易。

    :param side: str，交易方向 ("buy", "sell", "close")。
    :param reset: bool，是否重置警告标志位。
    :return: bool，是否有权限交易。
    """
    global trade_auth_warning
    LOGGING = hold_info.LOGGING

    # 重置输出标志位
    if reset:
        trade_auth_warning = None
        return

    tradeFlag = hold_info.newest("tradeFlag")

    if tradeFlag != "build" and side == "close":
        LOGGING.info(f"<{side}>: trade approved")
        return True

    # 检查是否有未同步的挂单
    pending_orders = sqlManager.filter_record(state="live") + sqlManager.filter_record(state="partially_filled")
    if pending_orders:
        return _log_warning(f"<{side}>: no access to trade, 数据库中仍然有挂单未同步")

    # 定义交易权限规则
    trade_rules = {
        "all-auth": lambda s: True,
        "no-auth": lambda s: False,
        "build": lambda s: s == "buy",
        "buy-only": lambda s: s == "buy",
        "sell-only": lambda s: s == "sell",
    }

    # 检查权限规则
    is_authorized = trade_rules.get(tradeFlag, lambda s: False)(side)
    if is_authorized:
        LOGGING.info(f"<{side}>: trade approved")
        return True

    # 未授权的情况
    return _log_warning(f"<{side}>: no access to trade ({tradeFlag})")


def _log_warning(msg):
    """
    日志记录工具函数，避免重复记录。

    :param msg: str，警告信息。
    :param logger: logging.Logger，日志记录器。
    :return: bool，总是返回 False。
    """
    LOGGING = hold_info.LOGGING

    global trade_auth_warning
    if msg != trade_auth_warning:
        LOGGING.warning(msg)
        trade_auth_warning = msg
    return False


def timed_task():
    bj_tz = timezone(timedelta(hours=8))
    now_bj = datetime.now().astimezone(bj_tz)
    # today = now_bj.day  # 当前月份的第几天
    hour_of_day = now_bj.hour  # 第几时
    minute = now_bj.minute  # 第几分

    if hour_of_day in [0, 4, 8, 12, 16, 20] and minute == 2:
        # if hour_of_day in [1, 4, 8, 12, 16, 20, 13] and minute == 1:
        target_stock = hold_info.target_stock
        DayStamp = hold_info.DayStamp

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        if DayStamp is not None and current_time == DayStamp:
            return

        LOGGING = hold_info.LOGGING
        hold_info.DayStamp = current_time
        redis_okx = redis.Redis.from_url(redis_url)
        redis_okx.hset(f"common_index:{target_stock}", 'last_read_time', current_time)
        LOGGING.info(f"到点了: {current_time} ")

        # 重置trade_auth输出权限
        trade_auth(reset=True)

        # 取消未成交的挂单
        check_state(target_stock, withdraw_order=True, LOGGING=LOGGING)

        # 开放交易权限
        hold_info.pull("tradeFlag", "all-auth")

        compute_sb_price(target_stock)


def sbb():
    LOGGING = hold_info.LOGGING
    target_stock = hold_info.target_stock
    LOGGING.info("超预算(减少数量)123456")
    LOGGING.info(target_stock)
