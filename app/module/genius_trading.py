# 导入日志配置
import logging.config




import os
import sys
import logging.config

from pathlib import Path
# 锁定环境变量路径
project_path = Path(__file__).resolve().parent  # 此脚本的运行"绝对"路径
# print(project_path)
dotenv_path = os.path.join(project_path, '../')
sys.path.append(dotenv_path)

from utils.logging_config import Logging_dict
import time
import datetime
import pytz


# logging.config.dictConfig(Logging_dict)
# LOGGING = logging.getLogger("app_01")


class LOGGING:
    @staticmethod
    def info(message):
        print(message)



def beijing_time(timestamp_ms):
    # 将毫秒时间戳转换为秒时间戳
    timestamp_s = int(timestamp_ms) / 1000.0

    # 创建 UTC 时间对象
    utc_time = datetime.datetime.utcfromtimestamp(timestamp_s)

    # 设置时区为北京时间（东八区）
    beijing_tz = pytz.timezone('Asia/Shanghai')
    beijing_time = utc_time.replace(tzinfo=pytz.utc).astimezone(beijing_tz)

    # 格式化输出
    formatted_time = beijing_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    return formatted_time


class GeniusTrader:
    def __init__(self):
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

        api_key = os.getenv('API_KEY')
        secret_key = os.getenv('SECRET_KEY')
        passphrase = os.getenv('PASSPHRASE')
        proxy = "http://127.0.0.1:7890"
        flag = "0"  # 实盘: 0, 模拟盘: 1

        self.tradeAPI = Trade.TradeAPI(api_key, secret_key, passphrase, False, flag, proxy=proxy, debug=False)
        self.accountAPI = Account.AccountAPI(api_key, secret_key, passphrase, False, flag, proxy=proxy, debug=False)
        self.publicDataAPI = PublicData.PublicAPI(flag=flag, proxy=proxy, debug=False)
        self.marketDataAPI = MarketData.MarketAPI(flag=flag, proxy=proxy, debug=False)

        self.wilson_favourite_stock_list = []
        self.cash_resources = 0

    def account(self):
        """账户信息"""
        LOGGING.info("\n")

        result = self.accountAPI.get_account_balance()
        # LOGGING.info(result)

        data = result['data'][0]
        totalEq = data['totalEq']
        LOGGING.info("=====================资金用户===========================")
        totalEq = round(float(totalEq), 2)
        LOGGING.info(f'总资产: {totalEq} 美元')

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
                LOGGING.info(f"现金储备: {balance} USDT")
            else:
                # LOGGING.info(f"币种: {currency}, 总权益: {balance}, 可用余额: {cashBal}, 可用保证金: {availEq}")
                LOGGING.info(f"{currency}, 权益: {balance}, 现价: {eqUsd} USDT")

    def stock_handle_info(self, target_stock):
        """个股持仓信息"""

        sort_name = target_stock.split('-')[0]
        result = self.accountAPI.get_account_balance()
        # LOGGING.info(result)

        details = result['data'][0]['details']
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
                LOGGING.info(f"现金储备: {balance} USDT")
            if currency == sort_name:
                LOGGING.info(f"{currency}, 权益: {balance}, 现价: {eqUsd} USDT")

    def stock_info(self, target_stock):
        """个股信息"""
        LOGGING.info("\n")

        # 基本信息
        result = self.accountAPI.get_instruments(instType="SPOT", instId=target_stock)
        min_account = float(result['data'][0]['minSz'])
        instId = result['data'][0]['instId']
        state = result['data'][0]['state']
        state = "可交易" if state == "live" else state == "不可交易"
        LOGGING.info(f"{instId}[{state}]")
        LOGGING.info(f"最小下单数量: {min_account}")


        # 获取单个产品行情信息,成交价，成交量什么的
        result = self.marketDataAPI.get_ticker(instId=target_stock)
        # print(result)
        last_price = result['data'][0]['last']
        LOGGING.info(f"现成交价: {last_price}")


        # 限价
        result = self.publicDataAPI.get_price_limit(instId=target_stock,)
        try:
            buyLmt_str = result['data'][0]['buyLmt']
            buyLmt = float(buyLmt_str)
            sellLmt_str = result['data'][0]['sellLmt']
            sellLmt = float(sellLmt_str)
            average_price = 0.5 * (buyLmt + sellLmt)
            # forecast_transaction_price = round(min_account * average_price, 4)
            forecast_transaction_price = round(min_account * last_price, 4)
            LOGGING.info(f"最高买价: {buyLmt_str}")
            LOGGING.info(f"最低卖价: {sellLmt_str}")
            LOGGING.info(f"均价: {round(average_price, 10)}")
            LOGGING.info(f"预计下单价格(最少): {forecast_transaction_price} USDT")

            if forecast_transaction_price < 3 and min_account > 100:
                dicter = {
                    "target_stock": target_stock,
                    "预测下单价格": forecast_transaction_price,
                    "最小下单数量": min_account
                }
                self.wilson_favourite_stock_list.append(dicter)
        except Exception as e:
            # LOGGING.info(e)
            pass


        # try:
        #     fee_rates = self.accountAPI.get_fee_rates(
        #         instType="SPOT",
        #         instId=target_stock
        #     )
        #     maker = fee_rates['data'][0]['maker']
        #     taker = fee_rates['data'][0]['taker']
        #     maker = "{:.2%}".format(abs(float(maker)))
        #     taker = "{:.2%}".format(abs(float(taker)))
        #     LOGGING.info(f"挂单费率: {maker}\n吃单费率(立即成交): {taker}")
        # except Exception as e:
        #     # LOGGING.info(e)
        #     pass

    def stock_candle(self, target_stock, after = None):
        if after == None:
            after = ""

        # 获取交易产品历史K线数据
        result = self.marketDataAPI.get_history_candlesticks(
            instId=target_stock,
            bar="1D",
            after=after,
            # after="1723046400000"
        )
        data = result['data']
        total = []
        for item in data:
            total.append(item[:5])

        # LOGGING.info(result)
        # LOGGING.info(total)
        return total

    def total_trade_market(self):
        """所有股票行情"""

        result = self.accountAPI.get_instruments(instType="SPOT")  # 无instId表示获取首页所有产品
        stock_list = result['data']
        for item in stock_list:
            instId = item['instId']
            self.stock_info(instId)

        for item in self.wilson_favourite_stock_list:
            LOGGING.info(item['target_stock'])
            LOGGING.info(item['预测下单价格'])
            LOGGING.info(item['最小下单数量'])
            LOGGING.info("\n")

    def buy_order(self, target_stock, amount, price=None):
        """买入"""
        LOGGING.info("\n")

        order_type = "limit"
        tgtCcy = ""
        if price is None:
            order_type = "market"
            tgtCcy = "base_ccy"

        timestamp = int(time.time())
        sort_name = target_stock.split("-")[0]
        client_order_id = f"{sort_name}{timestamp}"

        result = self.tradeAPI.place_order(
            instId=target_stock,
            tdMode="cash",
            clOrdId=client_order_id,
            side="buy",
            ordType=order_type,
            sz=str(amount),
            px=str(price),
            tgtCcy=tgtCcy
        )

        if result['code'] == '0':
            LOGGING.info("下单成功")
            LOGGING.info(result)
            self.execution_result(result)
            self.stock_handle_info(target_stock)
        else:
            sMsg = result["data"][0]["sMsg"]
            LOGGING.info(f"下单失败: {sMsg}")
            LOGGING.info(result)



    def sell_order(self, target_stock, amount, price=None):
        """卖出"""
        LOGGING.info("\n")

        order_type = "limit"
        if price is None:
            order_type = "market"

        timestamp = int(time.time())
        sort_name = target_stock.split("-")[0]
        client_order_id = f"{sort_name}{timestamp}"

        result = self.tradeAPI.place_order(
            instId=target_stock,
            tdMode="cash",
            clOrdId=client_order_id,
            side="sell",
            ordType=order_type,
            sz=str(amount),
            px=str(price)
        )

        if result['code'] == '0':
            LOGGING.info("下单成功")
            LOGGING.info(result)
            self.execution_result(result)
            self.stock_handle_info(target_stock)
        else:
            sMsg = result["data"][0]["sMsg"]
            LOGGING.info(f"下单失败: {sMsg}")
            LOGGING.info(result)


    def execution_result(self, result_dict):
        """执行结果"""
        LOGGING.info("\n")

        # time.sleep(1)
        order_id = result_dict['data'][0]["ordId"]
        client_order_id = result_dict['data'][0]["clOrdId"]
        target_stock = client_order_id[:-10] + "-USDT"

        result = self.tradeAPI.get_order(instId=target_stock, ordId=order_id)
        # LOGGING.info(result)

        deal_data = result['data'][0]

        side = deal_data["side"]
        side = "买入" if side == "buy" else "卖出"
        price_str = deal_data["fillPx"] if deal_data["ordType"] == "market" else deal_data["px"]
        price = float(price_str)
        account = float(deal_data["sz"])

        state = deal_data["state"]
        state = "已成交" if state == "filled" else state
        state = "等待成交" if state == "live" else state
        state = "已撤单" if state == "canceled" else state

        create_time = deal_data["cTime"]
        create_time = beijing_time(create_time)
        fill_time = "未执行" if deal_data["fillTime"] == '' else beijing_time(deal_data["fillTime"])

        # LOGGING.info(f"{client_order_id[:-10]}: {side}[{state}]")
        LOGGING.info(f"{client_order_id[:-10]}")
        LOGGING.info(f"{side}[{state}]")
        LOGGING.info(f"委托价格: {price_str}")
        LOGGING.info(f"委托数量: {account}")
        LOGGING.info(f"共{side}: {round(price * account, 3)} USDT")
        LOGGING.info(f"创建时间: {create_time}")
        LOGGING.info(f"成交时间: {fill_time}")


if __name__ == '__main__':
    # target_stock = "FLOKI-USDT"
    # target_stock = "LUNC-USDT"
    target_stock = "OMI-USDT"

    genius_trader = GeniusTrader()
    genius_trader.account()

    # 获取整个市场的报价
    # genius_trader.total_trade_market()

    genius_trader.stock_info(target_stock)
    # genius_trader.stock_candle(target_stock)
    # genius_trader.buy_order(target_stock, amount=2500)
    # genius_trader.sell_order(target_stock, amount=1080)

    # 查看订单执行结果
    # genius_trader.execution_result(result_dict)
