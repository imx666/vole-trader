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

    timestamp = int(time.time())
    order_type = "market"
    client_order_id = f"FLOKI{timestamp}"

    tradeAPI = Trade.TradeAPI(api_key, secret_key, passphrase, False, flag, proxy=proxy)
    number = 10001
    money = 0.000225

    # 现货模式限价单
    result = tradeAPI.place_order(
        instId=target_stock,
        tdMode="cash",
        clOrdId=client_order_id,
        side="sell",
        ordType="limit",
        sz=str(number),
        px=str(money)
    )
    print("下单结果")
    print(result)

    order_id = result['data'][0]["ordId"]

    # order_id = "1980101453107200000"

    result = tradeAPI.get_order(
        instId=target_stock,
        ordId=order_id
    )
    print("订单详情")
    print(result)

