from datetime import datetime
import time
import redis

from module.genius_trading import GeniusTrader
from module.trade_records import TradeRecordManager

# 交易api
geniusTrader = GeniusTrader("Assistant")

# 数据库记录
sqlManager = TradeRecordManager("Assistant")


# sqlManager = TradeRecordManager("TURTLE")

class LOGGING_2:
    @staticmethod
    def info(message):
        print(message)

    @staticmethod
    def error(message):
        print(message)


class TradeAssistant:
    # def __init__(self, sqlManager, geniusTrader, trade_type):
    def __init__(self, strategy_name, target_stock, trade_type, LOGGING=None):
        global geniusTrader, sqlManager
        sqlManager.strategy = strategy_name
        sqlManager.target_stock = target_stock
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
        # probable_price = (self.buyLmt + self.sellLmt) / 2
        # self.LOGGING.info(f"现价(可能): {round(probable_price, 6)}")
        self.LOGGING.info(f"现价: {self.now_price}")
        self.LOGGING.info(f"目标价: {target_market_price}, 数量: {amount}")
        # self.LOGGING.info(f"买限: {self.buyLmt}, 卖限: {self.sellLmt}")

    def sell(self, operation, execution_cycle, target_market_price, ratio, remark=None):
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
        client_order_id, timestamp_ms = self.geniusTrader.sell_order(amount=amount, price=target_market_price)

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

    def buy(self, operation, execution_cycle, target_market_price, amount, remark=None):
        if self.trade_type == "simulate":
            self.simulate(execution_cycle, operation, target_market_price, amount)
            return

        self.msg = operation if remark is None else remark
        self.show_moment(target_market_price, amount)
        client_order_id, timestamp_ms = self.geniusTrader.buy_order(amount=amount, price=target_market_price)

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

latest_update_time = time.time()


def get_real_time_info(target_stock, LOGGING):
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
    if now_price > 1000:
        return 1
    if now_price > 100:
        return 0.2
    if now_price > 10:
        return 0.1
    if now_price > 1:
        return 0.01
    return now_price / 1000

from utils.url_center import redis_url


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

