# 导入日志配置
# import logging.config
# from unittest import result
#
# from utils.logging_config import Logging_dict
import time
#
# logging.config.dictConfig(Logging_dict)
# LOGGING = logging.getLogger("app_01")


class GeniusTrader:
    def __init__(self):
        import os
        from pathlib import Path
        from dotenv import load_dotenv

        project_path = Path(__file__).resolve().parent  # 此脚本的运行"绝对"路径
        dotenv_path = os.path.join(project_path, '../../.env.dev')  # 指定.env.dev文件的路径

        # 载入环境变量
        load_dotenv(dotenv_path)

        api_key = os.getenv('API_KEY')
        secret_key = os.getenv('SECRET_KEY')
        passphrase = os.getenv('PASSPHRASE')
        proxy = "http://127.0.0.1:7890"

        import okx.Trade as Trade
        import okx.Account as Account
        flag = "0"  # live trading: 0, demo trading: 1

        self.tradeAPI = Trade.TradeAPI(api_key, secret_key, passphrase, False, flag, proxy=proxy)
        self.accountAPI = Account.AccountAPI(api_key, secret_key, passphrase, False, flag, proxy=proxy)

        # return tradeAPI, accountAPI

    def account(self):
        result =  self.accountAPI.get_account_balance()
        print(result)

    def buy_order(self, target_stock, amount, price):
        # amount = 24001
        # price = 0.000225

        timestamp = int(time.time())
        order_type = "limit"
        client_order_id = f"FLOKI{timestamp}"

        # tradeAPI, accountAPI = login()

        # 现货模式限价单
        result = self.tradeAPI.place_order(
            instId=target_stock,
            tdMode="cash",
            clOrdId=client_order_id,
            side="buy",
            ordType=order_type,
            sz=str(amount),
            px=str(price)
        )
        print("下单结果")
        print(result)

    def sell_order(self, target_stock, amount, price):
        # amount = 24001
        # price = 0.000225

        timestamp = int(time.time())
        order_type = "limit"
        client_order_id = f"FLOKI{timestamp}"

        # tradeAPI, accountAPI = login()
        # tradeAPI = Trade.TradeAPI(api_key, secret_key, passphrase, False, flag, proxy=proxy)

        # 现货模式限价单
        result = self.tradeAPI.place_order(
            instId=target_stock,
            tdMode="cash",
            clOrdId=client_order_id,
            side="sell",
            ordType=order_type,
            sz=str(amount),
            px=str(price)
        )
        print("下单结果")
        print(result)

    def execution_result(self, result_dict):

        order_id = result_dict['data'][0]["ordId"]
        # order_id = result_dict

        result = self.tradeAPI.get_order(
            instId=target_stock,
            ordId=order_id
        )
        print("执行结果")
        print(result)


if __name__ == '__main__':
    target_stock = "FLOKI-USDT"

    genius_trader = GeniusTrader()
    # id="1980101453107200000"
    # genius_trader.execution_result(result_dict)
    genius_trader.account()

