# 导入日志配置
import logging.config
from utils.logging_config import Logging_dict
import time
logging.config.dictConfig(Logging_dict)
LOGGING = logging.getLogger("app_01")

from datetime import datetime




if __name__ == '__main__':
    import os
    from pathlib import Path
    from dotenv import load_dotenv

    project_path = Path(__file__).resolve().parent  # 此脚本的运行"绝对"路径
    dotenv_path = os.path.join(project_path, '../.env.dev')  # 指定.env.dev文件的路径

    # 载入环境变量
    load_dotenv(dotenv_path)


    api_key = os.getenv('API_KEY')
    secret_key = os.getenv('SECRET_KEY')
    passphrase = os.getenv('PASSPHRASE')
    proxy = "http://127.0.0.1:7890"

    target_stock = "FLOKI-USDT"

    import okx.Account as Account
    import okx.Trade as Trade
    flag = "0"  # live trading: 0, demo trading: 1
    accountAPI = Account.AccountAPI(api_key, secret_key, passphrase, False, flag, proxy=proxy)


    # 获取FLOKI币的信息，不包括价格
    # result = accountAPI.get_instruments(instType="SPOT")  #无instId表示获取首页所有产品
    result = accountAPI.get_instruments(instType="SPOT", instId=target_stock)
    print("获取产品数据")
    print(result)

    # current_time = datetime.now().strftime("%Y-%m-%d--%H-%M-%S")
    current_time = datetime.now().strftime("%Yy%mm%dd%Hh%Mm%Ss")
    timestamp = int(time.time())
    order_type = "market"
    client_order_id = f"FLOKI{timestamp}"

    tradeAPI = Trade.TradeAPI(api_key, secret_key, passphrase, False, flag, proxy=proxy)
    number = 24001
    money = 0.000225

    # 现货模式限价单
    result = tradeAPI.place_order(
        instId=target_stock,
        tdMode="cash",
        clOrdId=client_order_id,
        side="buy",
        ordType="limit",
        sz=str(number),
        px=str(money)
    )
    print("下单结果")
    print(result)

    order_id = result['data'][0]["ordId"]

    result = tradeAPI.get_order(
        instId=target_stock,
        ordId=order_id
    )
    print("订单详情")
    print(result)

    # # 下单
    # import okx.SpreadTrading as SpreadTrading
    # spreadAPI = SpreadTrading.SpreadTradingAPI(api_key, secret_key, passphrase, False, flag, proxy=proxy)
    #
    # tradeAPI = Trade.TradeAPI(api_key, secret_key, passphrase, False, flag)
    # result = spreadAPI.place_order(sprdId=target_stock,
    #                                 # instId=target_stock,
    #                                side='buy', ordType=order_type,
    #                                sz='1.5')  # market市场价 的话，就没有px这个参数。px是数量，sz是总价，用usdt结算
    #
    # # result = spreadAPI.place_order(sprdId='BTC-USDT_BTC-USDT-SWAP',
    # #                                clOrdId=client_order_id, side='buy', ordType=order_type,
    # #                                px='2', sz='2')  # market市场价 的话，就没有px这个参数
    # print("下单结果")
    # print(result)

    # print("订单详情")
    # order_id = result['data'][0]["ordId"]
    # # 获取订单详情
    # result = spreadAPI.get_order_details(ordId=order_id)
    # print(result)