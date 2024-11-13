# 导入日志配置
import logging.config
from utils.logging_config import Logging_dict
logging.config.dictConfig(Logging_dict)
LOGGING = logging.getLogger("app_01")





if __name__ == '__main__':
    # 指定.env.dev文件的路径
    from pathlib import Path
    from dotenv import load_dotenv

    project_path = Path(__file__).resolve().parent  # 此脚本的运行"绝对"路径
    # project_path = os.getcwd()  # 此脚本的运行的"启动"路径
    # print(project_path)

    import os
    dotenv_path = os.path.join(project_path, '../.env.dev')

    # 载入环境变量
    load_dotenv(dotenv_path)



    # import okx.MarketData as MarketData
    # flag = "1"  # live trading: 0, demo trading: 1
    # marketDataAPI = MarketData.MarketAPI(flag=flag)
    # result = marketDataAPI.get_tickers(instType="SPOT")
    # print(result)

    api_key = os.getenv('API_KEY')
    secret_key = os.getenv('SECRET_KEY')
    passphrase = os.getenv('PASSPHRASE')
    import okx.Account as Account
    flag = "0"  # live trading: 0, demo trading: 1
    accountAPI = Account.AccountAPI(api_key, secret_key, passphrase, False, flag, proxy="http://127.0.0.1:7890")
    result = accountAPI.get_account_balance()
    print(result)