import time
# import datetime
from datetime import datetime

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
    # amount = Column(Numeric(16, 10))  # 数量，使用 Float 类型
    amount = Column(Numeric(16, 7))  # 数量，使用 Float 类型
    price = Column(Numeric(16, 10))  # 价格，使用 Float 类型
    value = Column(Float)  # 成交金额，也建议使用 Float 类型
    fee = Column(Numeric(16, 7))  # 价格，使用 Float 类型


    def __repr__(self):
        return f"<TradeRecord(id={self.id}, execution_cycle='{self.execution_cycle}', target_stock='{self.target_stock}', operation='{self.operation}', " \
               f"state='{self.state}', create_time='{self.create_time}', fill_time='{self.fill_time}', " \
               f"client_order_id='{self.client_order_id}', price={self.price}, amount={self.amount}, " \
               f"value={self.value}, fee={self.fee}, strategy='{self.strategy}')>"


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



DATABASE_URL = 'mysql+pymysql://root:123456@172.155.0.3:3306/trading_db'
engine = create_engine(DATABASE_URL, pool_recycle=3600)
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建所有定义的表
Base.metadata.create_all(bind=engine)




class TradeRecordManager:
    def __init__(self, target_stock, strategy_name=None):
        self.session = Session()
        self.target_stock = target_stock
        self.strategy = strategy_name

    def __del__(self):
        self.session.close()

    def generate_execution_cycle(self, strategy_name):
        """生成唯一的 execution_cycle 编号"""
        today = datetime.now().strftime('%Y%m%d')
        last_record = self.session.query(TradeRecord).filter(
            TradeRecord.execution_cycle.like(f'{strategy_name}_{today}%')
        ).order_by(TradeRecord.id.desc()).first()

        if last_record:
            last_number = int(last_record.execution_cycle.split('_')[-1])
            new_number = last_number + 1
        else:
            new_number = 1

        return f"{strategy_name}_{today}_{new_number:04d}"

    def last_execution_cycle(self, strategy_name):
        """最后的的 execution_cycle 编号"""
        last_record = self.session.query(TradeRecord).filter(
            TradeRecord.execution_cycle.like(f'{strategy_name}%')
        ).order_by(TradeRecord.create_time.desc()).first()
        if last_record:
            name = last_record.execution_cycle
            # print(name)
            return name
        return None

    def filter_record(self, state):
        record_list = []
        filtered_records = (
            self.session.query(TradeRecord)
            .filter(TradeRecord.target_stock == self.target_stock)
            .filter(TradeRecord.state == state)
            .all()
        )

        # 打印结果
        for record in filtered_records:
            # print(record.client_order_id)
            record_list.append(record.client_order_id)

        return record_list

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
                # if (operation == 'build' or operation == 'add') and record.state != 'canceled':
                    long_position += 1
                if operation == 'close':
                    return 0
            return long_position

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
                    total_max_amount += record.amount
                if operation == 'close':
                    raise Exception(f"trade_record实例不存在: {op}")
            return total_max_amount

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
                if operation == 'close':
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
                if operation == 'close':
                    raise Exception(f"trade_record实例不存在: {op}")
            return total_amount

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
                if operation == 'close':
                    raise Exception(f"trade_record实例不存在: {op}")
            return total_value

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
                if operation == 'reduce' and record.state != 'canceled':  # 可能部分成交
                    sell_time += 1
                if operation == 'close' and record.state != 'canceled':
                    return 0
                    # raise Exception(f"trade_record实例不存在: {op}")
                    # return -1
            return sell_time

        if op == 'build_price':
            trade_record = self.session.query(TradeRecord).filter(TradeRecord.target_stock == self.target_stock).filter(
                TradeRecord.execution_cycle == execution_cycle).filter(TradeRecord.state == "filled").filter(
                TradeRecord.operation == "build").first()
            if trade_record:
                open_price = float(trade_record.price)
                return open_price
            else:
                # return 0
                raise Exception(f"trade_record实例不存在: {op}")

        if op == 'last_hold_price':
            trade_record = self.session.query(TradeRecord).filter(TradeRecord.target_stock == self.target_stock).filter(
                TradeRecord.execution_cycle == execution_cycle).filter(TradeRecord.state == "filled").filter(
                TradeRecord.operation == "add").order_by(TradeRecord.create_time.desc()).first()
            if trade_record:
                open_price = float(trade_record.price)
                return open_price
            else:
                raise Exception(f"trade_record实例不存在: {op}")

    def add_trade_record(self, **kwargs):
        """添加一条新的交易记录"""
        trade_record = TradeRecord(
            execution_cycle=kwargs.get('execution_cycle'),
            target_stock=self.target_stock,
            operation=kwargs.get('operation'),
            state=kwargs.get('state'),
            create_time=kwargs.get('create_time'),
            fill_time=kwargs.get('fill_time'),
            client_order_id=kwargs.get('client_order_id'),
            price=kwargs.get('price'),
            amount=kwargs.get('amount'),
            value=kwargs.get('value'),
            fee=kwargs.get('fee'),
            strategy=self.strategy
        )
        self.session.add(trade_record)
        self.session.commit()
        print(f"Added trade record: {trade_record}")
        return trade_record

    # def add_trade_record(session, trade_record):
    #     """添加一条新的交易记录"""
    #     session.add(trade_record)
    #     session.commit()
    #     print(f"Added trade record: {trade_record}")

    def get_trade_record(self, trade_id):
        """获取指定ID的交易记录"""
        trade_record = self.session.query(TradeRecord).filter_by(id=trade_id).first()
        if trade_record:
            return trade_record
        else:
            print(f"No trade record found with id: {trade_id}")
            return None

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


def delete_trade_record(session, trade_id):
    """根据 ID 删除一条交易记录"""
    trade_record = session.query(TradeRecord).filter_by(id=trade_id).first()
    if trade_record:
        session.delete(trade_record)
        session.commit()
        print(f"Deleted trade record with ID {trade_id}")
    else:
        print(f"No trade record found with ID {trade_id}")


def update_trade_record(session, order_id, **kwargs):
    """根据 ID 更新一条交易记录"""
    trade_record = session.query(TradeRecord).filter_by(client_order_id=order_id).first()
    if trade_record:
        for key, value in kwargs.items():
            setattr(trade_record, key, value)
        session.commit()
        print(f"Updated trade record with ID {order_id}: {trade_record}")
    else:
        print(f"No trade record found with ID {order_id}")


def get_trade_record(session, trade_id):
    """根据 ID 获取一条交易记录"""
    trade_record = session.query(TradeRecord).filter_by(id=trade_id).first()
    if trade_record:
        return trade_record
    else:
        print(f"No trade record found with ID {trade_id}")
        return None


def list_trade_records(session):
    """列出所有交易记录"""
    trade_records = session.query(TradeRecord).all()
    if trade_records:
        for record in trade_records:
            print(record)
    else:
        print("No trade records found")


if __name__ == "__main__":
    strategy_name = 'sb'
    strategy_name = 'TURTLE'
    client_order_id = 'OMI12345'

    target_stock = "BTC"
    target_stock = "OMI-USDT"
    manager = TradeRecordManager(target_stock, strategy_name)


    # execution_cycle = manager.last_execution_cycle(strategy_name)  # 获取编号
    # last_hold_price = manager.get(execution_cycle, "last_hold_price")
    # last_hold_price = manager.get(execution_cycle, "open_price")
    # last_hold_price = manager.get(execution_cycle, "long_position")
    # last_hold_price = manager.get(execution_cycle, "sell_times")
    # last_hold_price = manager.get(execution_cycle, "rest_amount")
    # print(last_hold_price)


    execution_cycle = manager.generate_execution_cycle(strategy_name)

    timestamp_seconds = time.time()
    timestamp_ms = int(timestamp_seconds * 1000)  # 转换为毫秒

    # 将毫秒级时间戳转换为 datetime 对象
    create_time = datetime.fromtimestamp(timestamp_ms / 1000.0)

    # 添加一条新记录
    new_trade = manager.add_trade_record(
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
    # manager.update_trade_record(client_order_id, state='cancel', amount=1.5)

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
