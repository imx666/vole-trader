# 导入日志配置
import logging.config
from datetime import datetime

from utils.logging_config import Logging_dict

logging.config.dictConfig(Logging_dict)
LOGGING = logging.getLogger("app_01")

import redis

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

    from module.genius_trading import GeniusTrader

    target_stock = "LUNC-USDT"
    genius_trader = GeniusTrader()
    total_candle = genius_trader.stock_candle(target_stock)

    from module.common_index import get_DochianChannel, get_ATR

    history_max_price, history_min_price = get_DochianChannel(total_candle)
    ATR = get_ATR(total_candle)


    from module.redis_url import redis_url
    redis_okx = redis.Redis.from_url(redis_url)

    redis_okx.hset('stock:LUNC-USDT', mapping={'history_max_price': history_max_price, 'history_min_price': history_min_price, 'ATR': ATR})

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    redis_okx.hset('stock:LUNC-USDT', 'update_time', current_time)



    # 获取单个字段的值
    name = redis_okx.hget('stock:LUNC-USDT', 'update_time')
    name = name.decode()
    print(name)

    # 获取整个哈希表的所有字段和值
    all_info = redis_okx.hgetall('stock:LUNC-USDT')

    # 解码每个键和值
    decoded_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in all_info.items()}
    print(decoded_data)

    history_max_price, history_min_price = float(decoded_data['history_max_price']),float(decoded_data['history_min_price'])
    ATR = float(decoded_data['ATR'])
    print(ATR)
    print(history_max_price)
    print(history_min_price)


