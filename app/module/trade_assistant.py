from datetime import datetime
import time

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
        self.msg = None
        
        if LOGGING is None:
            self.LOGGING = LOGGING_2
        else:
            self.LOGGING = LOGGING
            geniusTrader.LOGGING = LOGGING

    def show_moment(self, target_market_price, amount):
        if self.msg is not None:
            self.LOGGING.info(f"remark: {self.msg}")
        probable_price = (self.buyLmt + self.sellLmt) / 2
        self.LOGGING.info(f"现价(可能): {round(probable_price, 6)}")
        self.LOGGING.info(f"目标价: {target_market_price}, 数量: {amount}")
        self.LOGGING.info(f"买限: {self.buyLmt}, 卖限: {self.sellLmt}")

    def sell(self, execution_cycle, target_market_price, ratio, remark=None):
        total_max_amount = self.sqlManager.get(execution_cycle, "total_max_amount")
        target_amount = total_max_amount * ratio
        rest_amount = self.sqlManager.get(execution_cycle, "rest_amount")
        amount = rest_amount if rest_amount < target_amount else target_amount
        operation = "close" if rest_amount <= target_amount else "reduce"

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
