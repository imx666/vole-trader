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



logging.config.dictConfig(Logging_dict)
LOGGING = logging.getLogger("app_01")
# LOGGING.setLevel(logging.INFO)

def beijing_time(timestamp_ms):
    # 时间戳（以毫秒为单位）

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

        api_key = os.getenv('API_KEY')
        secret_key = os.getenv('SECRET_KEY')
        passphrase = os.getenv('PASSPHRASE')
        proxy = "http://127.0.0.1:7890"
        flag = "0"  # 实盘: 0, 模拟盘: 1

        self.tradeAPI = Trade.TradeAPI(api_key, secret_key, passphrase, False, flag, proxy=proxy)
        self.accountAPI = Account.AccountAPI(api_key, secret_key, passphrase, False, flag, proxy=proxy)
        self.publicDataAPI = PublicData.PublicAPI(flag=flag, proxy=proxy)

        self.wilson_favourite_stock_list = []

    def account(self):
        """账户信息"""

        result = self.accountAPI.get_account_balance()
        # print(result)

        data = result['data'][0]
        totalEq = data['totalEq']
        print("=====================资金用户===========================")
        totalEq = round(float(totalEq), 2)
        print(f'总资产: {totalEq} 美元')

        details = data['details']
        for item in details:
            currency = item['ccy']
            # availEq = item.get('availEq')
            # availEq = 0 if availEq == '' else availEq
            eqUsd = item.get('eqUsd')
            eqUsd = 0 if eqUsd == '' else eqUsd
            eqUsd = round(float(eqUsd), 2)

            balance = round(float(item['eq']), 2)
            # cashBal = round(float(item['cashBal']), 2)

            if currency == "USDT":
                print(f"现金储备: {balance} USDT")
            else:
                # print(f"币种: {currency}, 总权益: {balance}, 可用余额: {cashBal}, 可用保证金: {availEq}")
                print(f"{currency}, 持仓: {balance}, 现价: {eqUsd} USDT")

    def stock_handle_info(self, target_stock):
        """个股持仓信息"""

        sort_name = target_stock.split('-')[0]
        result = self.accountAPI.get_account_balance()
        # print(result)

        details = result['data'][0]['details']
        for item in details:
            currency = item['ccy']
            # availEq = item.get('availEq')
            # availEq = 0 if availEq == '' else availEq
            eqUsd = item.get('eqUsd')
            eqUsd = 0 if eqUsd == '' else eqUsd
            eqUsd = round(float(eqUsd), 2)

            balance = round(float(item['eq']), 2)
            # cashBal = round(float(item['cashBal']), 2)

            if currency == "USDT":
                print(f"现金储备: {balance} USDT")
            if currency == sort_name:
                print(f"{currency}, 持仓: {balance}, 现价: {eqUsd} USDT")

    def stock_info(self, target_stock):
        """个股信息"""

        result = self.accountAPI.get_instruments(instType="SPOT", instId=target_stock)
        min_account = float(result['data'][0]['minSz'])
        instId = result['data'][0]['instId']
        state = result['data'][0]['state']
        state = "交易中" if state == "live" else state == "不可交易"
        print(f"{instId}[{state}]\n最小下单数量: {min_account} 枚")

        result = self.publicDataAPI.get_price_limit(
            instId=target_stock,
        )

        try:
            buyLmt_str = result['data'][0]['buyLmt']
            buyLmt = float(buyLmt_str)
            sellLmt_str = result['data'][0]['sellLmt']
            sellLmt = float(sellLmt_str)
            average_price = 0.5 * (buyLmt + sellLmt)
            forecast_transaction_price = round(min_account * average_price, 4)
            print(f"最高买价: {buyLmt_str}")
            print(f"最低卖价: {sellLmt_str}")
            print(f"均价: {round(average_price, 10)}")
            print(f"预测下单价格: {forecast_transaction_price} USDT")

            if forecast_transaction_price < 3 and min_account > 100:
                dicter = {
                    "target_stock": target_stock,
                    "预测下单价格": forecast_transaction_price,
                    "最小下单数量": min_account
                }
                self.wilson_favourite_stock_list.append(dicter)
        except Exception as e:
            # print(e)
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
        #     print(f"挂单费率: {maker}\n吃单费率(立即成交): {taker}")
        # except Exception as e:
        #     # print(e)
        #     pass

    def total_trade_market(self):
        """所有股票行情"""

        result = self.accountAPI.get_instruments(instType="SPOT")  # 无instId表示获取首页所有产品
        stock_list = result['data']
        for item in stock_list:
            instId = item['instId']
            self.stock_info(instId)

        for item in self.wilson_favourite_stock_list:
            print(item['target_stock'])
            print(item['预测下单价格'])
            print(item['最小下单数量'])
            print("\n")

    def buy_order(self, target_stock, amount, price=None):
        """买入"""

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

        print(result)
        if result['code'] == '0':
            print("下单成功")
            self.execution_result(result)
            self.stock_handle_info(target_stock)
        else:
            sMsg = result["data"][0]["sMsg"]
            print(f"下单失败: {sMsg}")

    def sell_order(self, target_stock, amount, price=None):
        """卖出"""

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

        print(result)
        if result['code'] == '0':
            print("下单成功")
            self.execution_result(result)
            self.stock_handle_info(target_stock)
        else:
            sMsg = result["data"][0]["sMsg"]
            print(f"下单失败: {sMsg}")

    def execution_result(self, result_dict):
        """执行结果"""

        # time.sleep(1)
        order_id = result_dict['data'][0]["ordId"]
        client_order_id = result_dict['data'][0]["clOrdId"]
        target_stock = client_order_id[:-10] + "-USDT"

        result = self.tradeAPI.get_order(
            instId=target_stock,
            ordId=order_id
        )
        # print(result)

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

        print(f"{side}[{state}]")
        print(f"委托价格: {price_str}\n委托数量: {account}")
        print(f"共{side}: {round(price * account, 3)} USDT")
        print(f"创建时间: {create_time}\n成交时间: {fill_time}")


if __name__ == '__main__':
    # target_stock = "FLOKI-USDT"
    # target_stock = "LUNC-USDT"
    target_stock = "OMI-USDT"

    genius_trader = GeniusTrader()
    genius_trader.account()
    genius_trader.stock_info(target_stock)

    # 获取整个市场的报价
    # genius_trader.total_trade_market()

    # genius_trader.buy_order(target_stock, amount=3000,)
    # genius_trader.sell_order(target_stock, amount=1000, )

    # 查看订单执行结果
    # result_dict = {'code': '0', 'data': [
    #     {'clOrdId': 'FLOKI1731592106', 'ordId': '1982721545963864064', 'sCode': '0', 'sMsg': 'Order placed', 'tag': '',
    #      'ts': '1731592106717'}], 'inTime': '1731592106716989', 'msg': '', 'outTime': '1731592106718129'}
    # genius_trader.execution_result(result_dict)
