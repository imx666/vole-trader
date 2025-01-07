
import os
import sys

from pathlib import Path

# 锁定环境变量路径
project_path = Path(__file__).resolve().parent  # 此脚本的运行"绝对"路径
dotenv_path = os.path.join(project_path, '../')
sys.path.append(dotenv_path)

import time
from datetime import datetime
import pytz


# # 导入日志配置
# import logging.config
# from utils.logging_config import Logging_dict
# logging.config.dictConfig(Logging_dict)
# LOGGING = logging.getLogger("app_01")


class LOGGING_2:
    @staticmethod
    def info(message):
        print(message)

    @staticmethod
    def error(message):
        print(message)


def beijing_time(timestamp_ms):
    # 将毫秒时间戳转换为秒时间戳
    timestamp_s = int(timestamp_ms) / 1000.0

    # 创建 UTC 时间对象
    utc_time = datetime.utcfromtimestamp(timestamp_s)

    # 设置时区为北京时间（东八区）
    beijing_tz = pytz.timezone('Asia/Shanghai')
    beijing_time = utc_time.replace(tzinfo=pytz.utc).astimezone(beijing_tz)

    # 格式化输出
    formatted_time = beijing_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    return formatted_time


class GeniusTrader:
    def __init__(self, target_stock=None, LOGGING=None):
        import os
        from pathlib import Path
        from dotenv import load_dotenv
        project_path = Path(__file__).resolve().parent  # 此脚本的运行"绝对"路径
        dotenv_path = os.path.join(project_path, '../../.env.dev')  # 指定.env.dev文件的路径
        load_dotenv(dotenv_path)  # 载入环境变量

        import okx.Trade as Trade
        import okx.Account as Account
        import okx.PublicData as PublicData
        import okx.MarketData as MarketData

        # api_key = os.getenv('API_KEY')
        # secret_key = os.getenv('SECRET_KEY')
        api_key = os.getenv('API_KEY_quant')
        secret_key = os.getenv('SECRET_KEY_quant')
        passphrase = os.getenv('PASSPHRASE')
        flag = "0"  # 实盘: 0, 模拟盘: 1

        # api_key = os.getenv('API_KEY_moni')
        # secret_key = os.getenv('SECRET_KEY_moni')
        # passphrase = os.getenv('PASSPHRASE_moni')
        # flag = "1"  # 实盘: 0, 模拟盘: 1

        # PROXY_URL = "http://127.0.0.1:7890"
        # PROXY_URL = 'http://hddoxgop:40ye9ko0kudx@198.23.239.134:6540'
        LOCATION = os.getenv('LOCATION')
        if LOCATION == "CHINA":
            PROXY_URL = 'http://hddoxgop:40ye9ko0kudx@154.36.110.199:6853'
        else:
            PROXY_URL = None

        self.tradeAPI = Trade.TradeAPI(api_key, secret_key, passphrase, False, flag, proxy=PROXY_URL, debug=False)
        self.accountAPI = Account.AccountAPI(api_key, secret_key, passphrase, False, flag, proxy=PROXY_URL, debug=False)
        self.publicDataAPI = PublicData.PublicAPI(flag=flag, proxy=PROXY_URL, debug=False)
        self.marketDataAPI = MarketData.MarketAPI(flag=flag, proxy=PROXY_URL, debug=False)

        self.wilson_favourite_stock_list = []
        self.cash_resources = 0
        self.target_stock = target_stock
        if LOGGING is None:
            self.LOGGING = LOGGING_2
        else:
            self.LOGGING = LOGGING



    def account(self):
        """账户信息"""
        self.LOGGING.info("\n")

        result = self.accountAPI.get_account_balance()
        # self.LOGGING.info(result)

        data = result['data'][0]
        totalEq = data['totalEq']
        self.LOGGING.info("=====================资金用户===========================")
        totalEq = round(float(totalEq), 2)
        self.LOGGING.info(f'总资产: {totalEq} 美元')

        details = data['details']
        for item in details:
            currency = item['ccy']
            # availEq = item.get('availEq')
            # availEq = 0 if availEq == '' else availEq
            eqUsd = item.get('eqUsd')
            eqUsd = 0 if eqUsd == '' else eqUsd
            eqUsd = round(float(eqUsd), 2)

            balance = round(float(item['eq']), 2)
            self.cash_resources = balance
            # cashBal = round(float(item['cashBal']), 2)

            if currency == "USDT":
                self.LOGGING.info(f"现金储备: {balance} USDT")
            else:
                # self.LOGGING.info(f"币种: {currency}, 总权益: {balance}, 可用余额: {cashBal}, 可用保证金: {availEq}")
                self.LOGGING.info(f"{currency}, 权益(可交易): {balance}, 现价: {eqUsd} USDT")

    def stock_handle_info(self, custom_stock):
        """个股持仓信息"""
        self.LOGGING.info(f"{custom_stock} 持有信息")

        sort_name = custom_stock.split('-')[0]
        result = self.accountAPI.get_account_balance()
        # self.LOGGING.info(result)

        details = result['data'][0]['details']
        for item in details:
            currency = item['ccy']
            # availEq = item.get('availEq')
            # availEq = 0 if availEq == '' else availEq
            eqUsd = item.get('eqUsd')
            eqUsd = 0 if eqUsd == '' else eqUsd
            eqUsd = round(float(eqUsd), 2)

            balance = float(item['eq'])
            self.cash_resources = balance
            # cashBal = round(float(item['cashBal']), 2)

            if currency == "USDT":
                self.LOGGING.info(f"现金储备: {round(balance, 2)} USDT")
            if currency == sort_name:
                self.LOGGING.info(f"{currency}, 权益: {round(balance, 2)}, 现价: {eqUsd} USDT")
                return balance

    def stock_info(self, custom_stock):
        """个股信息"""
        self.LOGGING.info("\n")

        # 基本信息
        result = self.accountAPI.get_instruments(instType="SPOT", instId=custom_stock)
        min_account = float(result['data'][0]['minSz'])
        instId = result['data'][0]['instId']
        state = result['data'][0]['state']
        state = "可交易" if state == "live" else state == "不可交易"
        self.LOGGING.info(f"{instId}[{state}]")
        self.LOGGING.info(f"最小下单数量: {min_account}")

        # 获取单个产品行情信息,成交价，成交量什么的
        result = self.marketDataAPI.get_ticker(instId=custom_stock)
        # print(result)
        last_price = result['data'][0]['last']
        self.LOGGING.info(f"现成交价: {last_price}")

        # 限价
        result = self.publicDataAPI.get_price_limit(instId=custom_stock, )
        try:
            buyLmt_str = result['data'][0]['buyLmt']
            buyLmt = float(buyLmt_str)
            sellLmt_str = result['data'][0]['sellLmt']
            sellLmt = float(sellLmt_str)
            average_price = 0.5 * (buyLmt + sellLmt)
            # forecast_transaction_price = round(min_account * average_price, 4)
            forecast_transaction_price = round(min_account * last_price, 4)
            self.LOGGING.info(f"最高买价: {buyLmt_str}")
            self.LOGGING.info(f"最低卖价: {sellLmt_str}")
            self.LOGGING.info(f"均价: {round(average_price, 10)}")
            self.LOGGING.info(f"预计下单价格(最少): {forecast_transaction_price} USDT")

            if forecast_transaction_price < 3 and min_account > 100:
                dicter = {
                    "custom_stock": custom_stock,
                    "预测下单价格": forecast_transaction_price,
                    "最小下单数量": min_account
                }
                self.wilson_favourite_stock_list.append(dicter)
        except Exception as e:
            # self.LOGGING.info(e)
            self.LOGGING.info(f"查询限价失败，或无限价")
            pass

        # try:
        #     fee_rates = self.accountAPI.get_fee_rates(
        #         instType="SPOT",
        #         instId=custom_stock
        #     )
        #     maker = fee_rates['data'][0]['maker']
        #     taker = fee_rates['data'][0]['taker']
        #     maker = "{:.2%}".format(abs(float(maker)))
        #     taker = "{:.2%}".format(abs(float(taker)))
        #     self.LOGGING.info(f"挂单费率: {maker}\n吃单费率(立即成交): {taker}")
        # except Exception as e:
        #     # self.LOGGING.info(e)
        #     pass

    def stock_candle(self, custom_stock, after=None, period='1D'):
        if after is None:
            after = ""

        # 获取交易产品历史K线数据
        result = self.marketDataAPI.get_history_candlesticks(
            instId=custom_stock,
            bar=period,
            after=after,  # after是时间戳
        )
        data = result['data']
        total = []
        for item in data:
            # total.append(item[:5])
            total.append(item)

        return total

    def total_trade_market(self):
        """所有股票行情"""

        result = self.accountAPI.get_instruments(instType="SPOT")  # 无instId表示获取首页所有产品
        stock_list = result['data']
        stock_list_sort = [item["instId"] for item in stock_list]
        print(stock_list_sort)
        # for item in stock_list:
        #     instId = item['instId']
        #     self.stock_info(instId)

        # for item in self.wilson_favourite_stock_list:
        #     self.LOGGING.info(item['target_stock'])
        #     self.LOGGING.info(item['预测下单价格'])
        #     self.LOGGING.info(item['最小下单数量'])
        #     self.LOGGING.info("\n")

    def buy_order(self, amount, price=None, order_type="limit"):
        """买入"""
        self.LOGGING.info("\n")

        # order_type = "limit"
        tgtCcy = ""
        if price is None:
            order_type = "market"
            tgtCcy = "base_ccy"

        if order_type == "market":
            price = None
            tgtCcy = "base_ccy"

        timestamp_seconds = time.time()
        timestamp_ms = int(timestamp_seconds * 1000)  # 转换为毫秒
        sort_name = self.target_stock.split("-")[0]
        client_order_id = f"{sort_name}{timestamp_ms}"

        result = self.tradeAPI.place_order(
            instId=self.target_stock,
            tdMode="cash",
            clOrdId=client_order_id,
            side="buy",
            ordType=order_type,
            sz=str(amount),
            px=str(price),
            tgtCcy=tgtCcy
        )

        if result['code'] == '0':
            self.LOGGING.info(f"下单成功: {result}")
            # if order_type == "market":
            #     self.execution_result(result)
            # self.stock_handle_info(self.target_stock)
        else:
            sMsg = result["data"][0]["sMsg"]
            self.LOGGING.info(f"下单失败: {sMsg}")
            self.LOGGING.info(result)
            raise Exception(f"下单失败: {sMsg}")

        return client_order_id, timestamp_ms

    def sell_order(self, amount, price=None, order_type="limit"):
        """卖出"""
        self.LOGGING.info("\n")

        # order_type = "limit"
        if price is None:
            order_type = "market"

        if order_type == "market":
            price = None

        timestamp_seconds = time.time()
        timestamp_ms = int(timestamp_seconds * 1000)  # 转换为毫秒
        sort_name = self.target_stock.split("-")[0]
        client_order_id = f"{sort_name}{timestamp_ms}"

        result = self.tradeAPI.place_order(
            instId=self.target_stock,
            tdMode="cash",
            clOrdId=client_order_id,
            side="sell",
            ordType=order_type,
            sz=str(amount),
            px=str(price)
        )

        if result['code'] == '0':
            self.LOGGING.info(f"下单成功: {result}")
            # if order_type == "market":
            #     self.execution_result(result)
            # self.stock_handle_info(self.target_stock)
        else:
            sMsg = result["data"][0]["sMsg"]
            self.LOGGING.info(f"下单失败: {sMsg}")
            self.LOGGING.info(result)
            raise Exception(f"下单失败: {sMsg}")

        return client_order_id, timestamp_ms

    def cancel_order(self, client_order_id):
        # 撤单
        result = self.tradeAPI.cancel_order(instId=self.target_stock, clOrdId=client_order_id)
        if result['code'] == '0':
            self.LOGGING.info("撤单成功")
            self.LOGGING.info(result)
            # self.stock_handle_info(target_stock)
        else:
            sMsg = result["data"][0]["sMsg"]
            self.LOGGING.info(f"撤单失败: {sMsg}")
            self.LOGGING.info(result)
            # 抛出异常
            raise Exception(f"撤单失败: {sMsg}")

    def pending_order(self, custom_stock):
        # 查询所有未成交订单

        result = self.tradeAPI.get_order_list(
            instId=custom_stock,
        )

        deal_data_list = result['data']
        if len(deal_data_list) == 0:
            print(f"{custom_stock}: 暂无未成交订单")
            return

        pending_list = []
        for deal_data in deal_data_list:
            side = deal_data["side"]
            client_order_id = deal_data["clOrdId"]
            pending_list.append(client_order_id)

            side = "买入" if side == "buy" else "卖出"
            price_str = deal_data["fillPx"] if deal_data["ordType"] == "market" else deal_data["px"]
            price = float(price_str)
            account = float(deal_data["sz"])

            state = deal_data["state"]
            state = "已成交" if state == "filled" else state
            state = "部分成交" if state == "partially_filled" else state
            state = "等待成交" if state == "live" else state
            state = "已撤单" if state == "canceled" else state

            create_time = deal_data["cTime"]
            create_time = beijing_time(create_time)
            fill_time = "未执行" if deal_data["fillTime"] == '' else beijing_time(deal_data["fillTime"])
            self.LOGGING.info(f"\n")
            self.LOGGING.info(f"{custom_stock}")
            self.LOGGING.info(f"{side}[{state}]")
            self.LOGGING.info(f"订单号: {client_order_id}")
            self.LOGGING.info(f"委托价格: {price_str}")
            self.LOGGING.info(f"委托数量: {account}")
            self.LOGGING.info(f"共{side}: {round(price * account, 3)} USDT")
            self.LOGGING.info(f"创建时间: {create_time}")
            self.LOGGING.info(f"成交时间: {fill_time}")

            # if result['code'] == '0':
            #     self.LOGGING.info("查询成功")
            #     self.LOGGING.info(result)
            # else:
            #     sMsg = result["data"][0]["sMsg"]
            #     self.LOGGING.info(f"查询失败: {sMsg}")
            #     self.LOGGING.info(result)
        return pending_list

    def execution_result(self, result_dict=None, client_order_id=None, target_and_ordId=[]):
        """执行结果"""
        self.LOGGING.info("\n")

        if result_dict is not None:
            # order_id = result_dict['data'][0]["ordId"]
            client_order_id = result_dict['data'][0]["clOrdId"]
            target_stock = client_order_id[:-13] + "-USDT"
            # result = self.tradeAPI.get_order(instId=target_stock, ordId=order_id)
            result = self.tradeAPI.get_order(instId=target_stock, clOrdId=client_order_id)


        elif client_order_id is not None:
            target_stock = client_order_id[:-13] + "-USDT"
            result = self.tradeAPI.get_order(instId=target_stock, clOrdId=client_order_id)

            
        elif target_and_ordId is not []:
            target_stock=target_and_ordId[0]
            result = self.tradeAPI.get_order(instId=target_stock, ordId=target_and_ordId[1])

        else:
            return None
            # result = self.tradeAPI.get_order(instId=target_stock, clOrdId=client_order_id)

        if result['code'] != '0':
            # sMsg = result["data"][0]["sMsg"]
            sMsg = result['msg']
            self.LOGGING.info(result)
            raise Exception(f"查询失败: {sMsg}")

        self.LOGGING.info(result['msg'])

        deal_data = result['data'][0]
        side = deal_data["side"]
        side11 = "买入" if side == "buy" else "卖出"
        side222 = "花费" if side == "buy" else "收到"
        price_str = deal_data["fillPx"] if deal_data["ordType"] == "market" else deal_data["px"]
        price = float(price_str)
        amount = float(deal_data["sz"])
        fee = float(deal_data["fee"])

        state = deal_data["state"]
        state = "已成交" if state == "filled" else state
        state = "部分成交" if state == "partially_filled" else state
        state = "等待成交" if state == "live" else state
        state = "已撤单" if state == "canceled" else state

        create_time = deal_data["cTime"]
        create_time = beijing_time(create_time)
        fill_time = "未执行" if deal_data["fillTime"] == '' else beijing_time(deal_data["fillTime"])

        # self.LOGGING.info(f"{client_order_id[:-10]}: {side}[{state}]")
        self.LOGGING.info(f"{target_stock}")
        self.LOGGING.info(f"{side11}[{state}]")
        self.LOGGING.info(f"委托价格: {price_str}")
        self.LOGGING.info(f"委托数量: {amount}")
        # self.LOGGING.info(f"共{side}: {round(price * amount, 3)} USDT")
        self.LOGGING.info(f"共{side222}: {price * amount} USDT")
        if side11 == "卖出":
            fee = -fee
            self.LOGGING.info(f"手续费: {round(fee, 10)} USDT")
        else:
            fee = -fee * price  # 买入时，手续费是按照标的物计算的
            # self.LOGGING.info(f"手续费: {round(fee, 10)} {target_stock.split('-')[0]}")
            self.LOGGING.info(f"手续费: {round(fee, 10)} USDT")
        self.LOGGING.info(f"创建时间: {create_time}")
        self.LOGGING.info(f"成交时间: {fill_time}")

        return result


if __name__ == '__main__':
    strategy_name = "TURTLE"

    # target_stock = "FLOKI-USDT"
    # target_stock = "LUNC-USDT"
    target_stock = "OMI-USDT"

    genius_trader = GeniusTrader(target_stock)

    # from module.trade_records import TradeRecordManager
    # manager = TradeRecordManager(target_stock)

    # # 账户信息
    # genius_trader.account()

    # 获取整个市场的报价
    genius_trader.total_trade_market()

    # # 股票k线
    # genius_trader.stock_candle(target_stock)

    # # 个股信息
    # genius_trader.stock_info(target_stock)

    # # 个股持仓信息
    # amount = genius_trader.stock_handle_info(target_stock)
    # print(f"amount: {amount}")

    # # 买入
    # amount = 2200
    # target_market_price = 0.00012345
    # client_order_id, timestamp_ms = genius_trader.buy_order(amount=amount, price=target_market_price)
    # genius_trader.execution_result(client_order_id=client_order_id)

    # # 添加一条新记录
    # manager.add_trade_record(
    #     create_time=datetime.fromtimestamp(timestamp_ms / 1000.0),
    #     execution_cycle=manager.generate_execution_cycle(strategy_name),
    #     operation="build position",
    #     state="live",
    #     client_order_id=client_order_id,
    #     price=target_market_price,
    #     amount=amount,
    #     # value=1500.0,
    #     strategy=strategy_name
    # )

    # # 卖出
    # genius_trader.sell_order(target_stock, amount=amount, price=0.00069)

    # # 撤单
    # genius_trader.cancel_order(target_stock, client_order_id="OMI1732363988494")

    # # 查询未成交订单
    # genius_trader.pending_order(target_stock)

    # 查看订单执行结果
    # genius_trader.execution_result(target_and_ordId=["OMI-USDT","2006379750208077824"])
    # genius_trader.execution_result(target_and_ordId=["DOGE-USDT","2078711079121231872"])
    # genius_trader.execution_result(client_order_id="FLOKI1734759229556")
