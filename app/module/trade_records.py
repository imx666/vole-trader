import time
# import datetime
from datetime import datetime
from functools import wraps

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Numeric
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# 声明基类
Base = declarative_base()


# 定义数据模型
class TradeRecord(Base):
    __tablename__ = 'trade_records'

    id = Column(Integer, primary_key=True)
    strategy = Column(String(255))  # 使用策略
    execution_cycle = Column(String(255))  # 执行周期的唯一编号
    target_stock = Column(String(25))
    operation = Column(String(25))  # 操作类型，买入或卖出
    state = Column(String(25), default='live')  # 订单状态，如未成交、部分成交、已成交等
    create_time = Column(DateTime)
    fill_time = Column(DateTime)
    client_order_id = Column(String(255))  # 客户端订单ID
    amount = Column(Numeric(16, 8))  # 数量，使用 Float 类型
    price = Column(Numeric(16, 10))  # 价格，使用 Float 类型
    value = Column(Float)  # 成交金额，也建议使用 Float 类型
    fee = Column(Numeric(16, 7))  # 价格，使用 Float 类型
    remark = Column(String(255))  # 使用策略
    delta = Column(Float)  # 价格，使用 Float 类型
    profit_rate = Column(Float)  # 价格，使用 Float 类型

    def __repr__(self):
        return f"<TradeRecord(id={self.id}, execution_cycle='{self.execution_cycle}', target_stock='{self.target_stock}', operation='{self.operation}', " \
               f"state='{self.state}', create_time='{self.create_time}', fill_time='{self.fill_time}', " \
               f"client_order_id='{self.client_order_id}', price={self.price}, amount={self.amount}, " \
               f"value={self.value}, fee={self.fee}, strategy='{self.strategy}')>, remark='{self.remark}'), delta='{self.delta}'), profit_rate='{self.profit_rate}')>"


# from pathlib import Path
#
# BASE_DIR = Path(__file__).resolve().parent.parent.parent
# print(BASE_DIR)
#
# # 数据库连接配置
# # DATABASE_URL = 'sqlite:///trades.db'
# DATABASE_URL = f'sqlite:///{BASE_DIR}/data/trades.db'  # 这里使用 SQLite 作为示例，你可以根据需要更改
# print(DATABASE_URL)

# # 创建数据库引擎
# engine = create_engine(DATABASE_URL)

# # 创建会话工厂
# Session = sessionmaker(bind=engine)

# # 创建数据表
# Base.metadata.create_all(engine)

from utils.url_center import DATABASE_URL

# DATABASE_URL = 'mysql+pymysql://root:123456@172.155.0.3:3306/trading_db'
engine = create_engine(DATABASE_URL, pool_recycle=3600)
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建所有定义的表
Base.metadata.create_all(bind=engine)


def refresh_cache(method):
    """
    装饰器：在每次方法调用前刷新 SQLAlchemy 会话缓存。
    """

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        # 刷新会话缓存
        # self.session.close()  # 关闭当前会话
        # self.session = Session()  # 创建新会话
        # self.session.expire_all()
        # self.session.refresh(instance)
        # self.session.commit()
        self.session.commit()

        # 执行原方法
        return method(self, *args, **kwargs)

    return wrapper


class TradeRecordManager:
    def __init__(self, target_stock, strategy_name=None):
        self.session = Session()
        self.target_stock = target_stock
        self.strategy = strategy_name

    # def new_stock(self, new_stock):
    #     self.target_stock = new_stock

    def __del__(self):
        self.session.close()

    def generate_execution_cycle(self):
        """生成唯一的 execution_cycle 编号"""
        sort_name = self.target_stock.split('-')[0]
        today = datetime.now().strftime('%Y%m%d')
        last_record = self.session.query(TradeRecord).filter(
            TradeRecord.execution_cycle.like(f'{self.strategy}-{sort_name}-{today}%')
        ).order_by(TradeRecord.id.desc()).first()

        if last_record:
            last_number = int(last_record.execution_cycle.split('_')[-1])
            new_number = last_number + 1
        else:
            new_number = 1

        return f"{self.strategy}-{sort_name}-{today}_{new_number:04d}"

    def last_execution_cycle(self, strategy_name):
        """获取最后的的 execution_cycle 编号"""
        last_record = self.session.query(TradeRecord).filter(
            TradeRecord.execution_cycle.like(f'{strategy_name}%')
        ).order_by(TradeRecord.create_time.desc()).first()
        if last_record:
            name = last_record.execution_cycle
            # print(name)
            return name
        return None

    @refresh_cache
    def filter_record(self, state, new_stock=None):
        # print(12345, new_stock)
        if new_stock is None:
            new_stock = self.target_stock
        record_list = []
        filtered_records = (
            self.session.query(TradeRecord)
            .filter(TradeRecord.target_stock == new_stock)
            .filter(TradeRecord.state == state)
            .all()
        )

        # 打印结果
        for record in filtered_records:
            # print(record.client_order_id)
            record_list.append(record.client_order_id)

        return record_list

    @refresh_cache
    def get(self, execution_cycle, op):
        if op == 'long_position':
            long_position = 0
            filtered_records = (
                self.session.query(TradeRecord)
                .filter(TradeRecord.target_stock == self.target_stock)
                .filter(TradeRecord.execution_cycle == execution_cycle)
                .all()
            )
            for record in filtered_records:
                operation = record.operation
                if (operation == 'build' or operation == 'add') and record.state == 'filled':
                    long_position += 1
                if operation == 'close' and record.state == 'filled':
                    return 0
            return long_position

        if op == 'sell_times':
            sell_time = 0
            filtered_records = (
                self.session.query(TradeRecord)
                .filter(TradeRecord.target_stock == self.target_stock)
                .filter(TradeRecord.execution_cycle == execution_cycle)
                .all()
            )
            for record in filtered_records:
                operation = record.operation
                # if operation == 'reduce' and record.state != 'canceled':  # 可能部分成交，但是不能是live啊
                if operation == 'reduce' and record.state == 'filled':
                    sell_time += 1
                # if operation == 'close' and record.state != 'canceled':
                if operation == 'close' and record.state == 'filled':
                    return 0
                    # raise Exception(f"trade_record实例不存在: {op}")
            return sell_time

        if op == 'total_max_amount':
            total_max_amount = 0
            filtered_records = (
                self.session.query(TradeRecord)
                .filter(TradeRecord.target_stock == self.target_stock)
                .filter(TradeRecord.execution_cycle == execution_cycle)
                .all()
            )
            for record in filtered_records:
                operation = record.operation
                if (operation == 'build' or operation == 'add') and record.state == 'filled':
                    # print(record.amount)
                    total_max_amount += record.amount
                # if operation == 'close' and record.state == 'filled':
                #     raise Exception(f"trade_record实例不存在: {op}")
            return float(total_max_amount)

        if op == 'total_max_value':
            total_max_value = 0
            filtered_records = (
                self.session.query(TradeRecord)
                .filter(TradeRecord.target_stock == self.target_stock)
                .filter(TradeRecord.execution_cycle == execution_cycle)
                .all()
            )
            for record in filtered_records:
                operation = record.operation
                if (operation == 'build' or operation == 'add') and record.state == 'filled':
                    total_max_value += record.value
                if operation == 'close' and record.state == 'filled':
                    raise Exception(f"trade_record实例不存在: {op}")
            return total_max_value

        if op == 'rest_amount':
            total_amount = 0
            filtered_records = (
                self.session.query(TradeRecord)
                .filter(TradeRecord.target_stock == self.target_stock)
                .filter(TradeRecord.execution_cycle == execution_cycle)
                .all()
            )
            for record in filtered_records:
                operation = record.operation
                if (operation == 'build' or operation == 'add') and record.state == 'filled':
                    total_amount += record.amount
                if operation == 'reduce' and record.state == 'filled':
                    total_amount -= record.amount
                if operation == 'close' and record.state == 'filled':
                    raise Exception(f"trade_record实例不存在: {op}")
            return float(total_amount)

        if op == 'rest_value':
            total_value = 0
            filtered_records = (
                self.session.query(TradeRecord)
                .filter(TradeRecord.target_stock == self.target_stock)
                .filter(TradeRecord.execution_cycle == execution_cycle)
                .all()
            )
            for record in filtered_records:
                operation = record.operation
                if (operation == 'build' or operation == 'add') and record.state == 'filled':
                    total_value += record.value
                if operation == 'reduce' and record.state == 'filled':
                    total_value -= record.value
                if operation == 'close' and record.state == 'filled':
                    raise Exception(f"trade_record实例不存在: {op}")
            return total_value

        if op == 'build_price':
            filtered_records = (
                self.session.query(TradeRecord)
                .filter(TradeRecord.target_stock == self.target_stock)
                .filter(TradeRecord.execution_cycle == execution_cycle)
                .all()
            )
            for record in filtered_records:
                if record.operation == 'close' and record.state == 'filled':
                    raise Exception(f"trade_record: 此执行编号已存在close操作，请启用新的执行编号")
                    # return 0

            trade_record = self.session.query(TradeRecord).filter(TradeRecord.target_stock == self.target_stock).filter(
                TradeRecord.execution_cycle == execution_cycle).filter(TradeRecord.state == "filled").filter(
                TradeRecord.operation == "build").first()
            if trade_record:
                open_price = trade_record.price
                return float(open_price)
            else:
                return 0
                # raise Exception(f"trade_record实例不存在: {op}")

        if op == 'last_hold_price':  # 使用按时间倒序查询，即最晚的
            trade_record = self.session.query(TradeRecord).filter(TradeRecord.target_stock == self.target_stock).filter(
                TradeRecord.execution_cycle == execution_cycle).filter(TradeRecord.state == "filled").filter(
                TradeRecord.operation == "add").order_by(TradeRecord.create_time.desc()).first()
            if trade_record:
                open_price = trade_record.price
                return float(open_price)
            else:
                raise Exception(f"trade_record实例不存在: {op}")

        # if op == 'execution_state':
        #     filtered_records = (
        #         self.session.query(TradeRecord)
        #         .filter(TradeRecord.target_stock == self.target_stock)
        #         .filter(TradeRecord.execution_cycle == execution_cycle)
        #         .all()
        #     )
        #     for record in filtered_records:
        #         if record.operation == 'close' and record.state == 'filled':
        #             return "completed", record.client_order_id
        #     return "running", 0

        if op == 'balance_delta':
            total_value = 0
            filtered_records = (
                self.session.query(TradeRecord)
                .filter(TradeRecord.strategy == self.strategy)
                .filter(TradeRecord.target_stock == self.target_stock)
                .all()
            )
            for record in filtered_records:
                operation = record.operation
                if (operation == 'build' or operation == 'add') and record.state == 'filled':
                    total_value -= record.value
                if (operation == 'reduce' or operation == 'close') and record.state == 'filled':
                    total_value += record.value

            return total_value

        if op == 'delta':
            flag = 0
            spend_value = 0
            receive_value = 0
            filtered_records = (
                self.session.query(TradeRecord)
                .filter(TradeRecord.execution_cycle == execution_cycle)
                .filter(TradeRecord.strategy == self.strategy)
                .filter(TradeRecord.target_stock == self.target_stock)
                .all()
            )
            for record in filtered_records:
                operation = record.operation
                if (operation == 'build' or operation == 'add') and record.state == 'filled':
                    spend_value += record.value
                    print('add', record.value)
                if (operation == 'reduce' or operation == 'close') and record.state == 'filled':
                    receive_value += record.value
                    print('reduce', record.value)
                if operation == 'close' and record.state == 'filled':
                    flag = 1

            if flag == 0:
                raise Exception(f"trade_record: 此执行编号未存在close操作，无法计算delta, profit_rate")

            delta = receive_value - spend_value
            profit_rate = delta / spend_value
            return delta, profit_rate

    @refresh_cache
    def add_trade_record(self, **kwargs):
        """添加一条新的交易记录"""
        trade_record = TradeRecord(
            execution_cycle=kwargs.get('execution_cycle'),
            target_stock=self.target_stock,
            operation=kwargs.get('operation'),
            # state=kwargs.get('state'),  # 默认为live
            create_time=kwargs.get('create_time'),
            fill_time=kwargs.get('fill_time'),
            client_order_id=kwargs.get('client_order_id'),
            price=kwargs.get('price'),
            amount=kwargs.get('amount'),
            value=kwargs.get('value'),
            fee=kwargs.get('fee'),
            strategy=self.strategy,
            remark=kwargs.get('remark'),
        )
        self.session.add(trade_record)
        self.session.commit()
        print(f"Added trade record: {trade_record}")
        return trade_record

    @refresh_cache
    def get_trade_record(self, execution_cycle):
        """获取指定ID的交易记录"""
        trade_record = self.session.query(TradeRecord).filter_by(execution_cycle=execution_cycle).order_by(
            TradeRecord.create_time.desc()).first()

        if trade_record:
            return to_dict(trade_record)
        else:
            print(f"No trade record found with id: {execution_cycle}")
            return None

    @refresh_cache
    def update_trade_record(self, trade_id, **kwargs):
        """更新指定ID的交易记录"""
        trade_record = self.session.query(TradeRecord).filter_by(client_order_id=trade_id).first()
        if trade_record:
            for key, value in kwargs.items():
                if hasattr(trade_record, key):
                    setattr(trade_record, key, value)
            self.session.commit()
            print(f"Updated trade record: {trade_record}")
            return trade_record
        else:
            print(f"No trade record found with id: {trade_id}")
            return None

    def delete_trade_record(self, trade_id):
        """删除指定ID的交易记录"""
        trade_record = self.session.query(TradeRecord).filter_by(id=trade_id).first()
        if trade_record:
            self.session.delete(trade_record)
            self.session.commit()
            print(f"Deleted trade record with id: {trade_id}")
            return True
        else:
            print(f"No trade record found with id: {trade_id}")
            return False


def to_dict(instance):
    if instance is None:
        return None
    return {key: value for key, value in instance.__dict__.items() if not key.startswith('_')}



if __name__ == "__main__":
    strategy_name = 'sb'
    strategy_name = 'TURTLE'
    client_order_id = 'OMI12345'

    target_stock = "BTC"
    target_stock = "OMI-USDT"
    sqlManager = TradeRecordManager(target_stock, strategy_name)

    # execution_cycle = sqlManager.last_execution_cycle(strategy_name)  # 获取编号
    # last_hold_price = sqlManager.get(execution_cycle, "last_hold_price")
    # last_hold_price = sqlManager.get(execution_cycle, "open_price")
    # last_hold_price = sqlManager.get(execution_cycle, "long_position")
    # last_hold_price = sqlManager.get(execution_cycle, "sell_times")
    # last_hold_price = sqlManager.get(execution_cycle, "rest_amount")
    # print(last_hold_price)

    execution_cycle = sqlManager.generate_execution_cycle()

    timestamp_seconds = time.time()
    timestamp_ms = int(timestamp_seconds * 1000)  # 转换为毫秒

    # 将毫秒级时间戳转换为 datetime 对象
    create_time = datetime.fromtimestamp(timestamp_ms / 1000.0)

    # 添加一条新记录
    new_trade = sqlManager.add_trade_record(
        create_time=create_time,
        execution_cycle=execution_cycle,
        operation="BUY",
        state="FILLED",
        client_order_id=client_order_id,
        price=150.0,
        amount=10,
        value=1500.0,
        fee=0.001
    )

    # client_order_id = 'OMI12344'
    # # 更新一条交易记录
    # sqlManager.update_trade_record(client_order_id, state='cancel', amount=1.5)

    # # 获取一条交易记录
    # trade_record = get_trade_record(session, 1)
    # if trade_record:
    #     print(f"Fetched trade record: {trade_record}")

    # # 列出所有交易记录
    # list_trade_records(session)
    #
    # # 删除一条交易记录
    # delete_trade_record(session, 1)

    # # 查询数据
    # all_articles = session.query(TradeRecord).all()
    # print(all_articles)
