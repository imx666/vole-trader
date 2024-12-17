from datetime import datetime
import time


class LOGGING:
    @staticmethod
    def info(message):
        print(message)

    @staticmethod
    def error(message):
        print(message)


class TradeAssistant:
    def __init__(self, sqlManager, geniusTrader, trade_type):
        self.sqlManager = sqlManager
        self.geniusTrader = geniusTrader
        self.trade_type = trade_type
        self.buyLmt = None
        self.sellLmt = None
        self.msg = None

    def show_moment(self, target_market_price):
        if self.msg is not None:
            LOGGING.info(self.msg)
        LOGGING.info(f"目标价: {target_market_price}")
        LOGGING.info(f"buyLmt: {self.buyLmt}, sellLmt: {self.sellLmt}")
        probable_price = (self.buyLmt + self.sellLmt) / 2
        LOGGING.info(f"probable_price: {round(probable_price, 6)}")

    def sell(self, execution_cycle, target_market_price, ratio, remark=None):
        total_max_amount = self.sqlManager.get(execution_cycle, "total_max_amount")
        target_amount = round(total_max_amount * ratio, 3)
        rest_amount = self.sqlManager.get(execution_cycle, "rest_amount")
        amount = rest_amount if rest_amount < target_amount else target_amount
        operation = "close" if rest_amount < target_amount else "reduce"

        if self.trade_type == "simulate":
            self.simulate(execution_cycle, operation, target_market_price, amount)
            return

        client_order_id, timestamp_ms = self.geniusTrader.sell_order(amount=amount, price=target_market_price)
        self.msg = operation if remark is None else remark
        self.show_moment(target_market_price)

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

    def buy(self, operation, execution_cycle, target_market_price, amount, remark=None):
        if self.trade_type == "simulate":
            self.simulate(execution_cycle, operation, target_market_price, amount)
            return

        client_order_id, timestamp_ms = self.geniusTrader.buy_order(amount=amount, price=target_market_price)
        self.msg = operation if remark is None else remark
        self.show_moment(target_market_price)

        # 添加一条新记录
        self.sqlManager.add_trade_record(
            create_time=datetime.fromtimestamp(timestamp_ms / 1000.0),
            execution_cycle=execution_cycle,
            operation=operation,
            client_order_id=client_order_id,
            price=target_market_price,
            amount=amount,
            value=round(amount * target_market_price, 3),
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
