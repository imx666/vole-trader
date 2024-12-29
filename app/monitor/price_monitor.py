import asyncio
import time
from datetime import datetime
import socket

import redis
import websockets
import json

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 锁定系统运行路径
project_path = Path(__file__).resolve().parent  # 此脚本的运行"绝对"路径
dotenv_path = os.path.join(project_path, '../')
sys.path.append(dotenv_path)

dotenv_path = os.path.join(project_path, '../../.env.dev')  # 指定.env.dev文件的路径
load_dotenv(dotenv_path)  # 载入环境变量

import logging.config
from utils.logging_config import Logging_dict

logging.config.dictConfig(Logging_dict)
LOGGING = logging.getLogger(f"VoleTrader")

# 第一个参数是脚本名称，后续的是传入的参数
if len(sys.argv) > 1:
    target_stock = sys.argv[1]  # 这里会得到 '123'
    print(f"The argument target_stock is: {target_stock}")
else:
    print("Error: No arguments were passed. Please provide an target_stock and try again!")
    sys.exit(1)  # 使用非零状态码表示异常退出

# sort_name = target_stock.split('-')[0]

from utils.url_center import redis_url_fastest

# LOGGING = logging.getLogger(f"VoleTrader")

# target_stock = "LUNC-USDT"
# target_stock = "BTC-USDT"
# target_stock = "ETH-USDT"
# target_stock = "FLOKI-USDT"
# target_stock = "OMI-USDT"
# target_stock = "DOGE-USDT"
# target_stock = "PEPE-USDT"


redis_microsoft = redis.Redis.from_url(redis_url_fastest)


# timestamp_seconds = time.time()
# timestamp_ms = int(timestamp_seconds * 1000)  # 转换为毫秒
# redis_microsoft.hset(f"real_time_index:{target_stock}",
#                      mapping={
#                          'now_price': 0,
#                          'trading volume': 0,
#                          'update_time': timestamp_ms,
#                      })

def update_real_time_info(now_price, trading_volume):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamp_seconds = time.time()
    timestamp_ms = int(timestamp_seconds * 1000)  # 转换为毫秒
    redis_microsoft.hset(f"real_time_index:{target_stock}",
                         mapping={
                             'now_price': now_price,
                             'trading_volume': trading_volume,
                             'update_time': timestamp_ms,
                             'update_time(东八区)': current_time,
                         })


async def main():
    # 订阅产品频道的消息
    subscribe_msg = {
        "op": "subscribe",
        "args": [
            {
                "channel": "trades",
                # "instType": "FUTURES",  # 这里可以是SPOT, MARGIN, SWAP, FUTURES, OPTION之一
                "instId": target_stock
            }
        ]
    }
    while True:
        reconnect_attempts = 0
        try:
            async with websockets.connect('wss://ws.okx.com:8443/ws/v5/public') as websocket:
                # 发送订阅请求
                await websocket.send(json.dumps(subscribe_msg))
                subscribe_response = await websocket.recv()
                LOGGING.info(f"订阅响应: {subscribe_response}")
                LOGGING.info(f"持续跟踪价格中...")

                # 持续监听增量数据
                while True:
                    try:
                        # response = await websocket.recv()
                        response = await asyncio.wait_for(websocket.recv(), timeout=25)

                        # 将字符串转换为字典
                        data_dict = json.loads(response)

                        # os.system("clear")
                        # price = data_dict["data"][0]["px"]
                        # print(f"成交价格:{price}")
                        # print(f"成交数量:{num}")

                        now_price = float(data_dict["data"][0]["px"])
                        trading_volume = float(data_dict["data"][0]["sz"])

                        # LOGGING.info(f"now_price: {now_price}")
                        update_real_time_info(now_price, trading_volume)


                    # except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed) as e:
                    #     try:
                    #         await websocket.send('ping')
                    #         res = await websocket.recv()
                    #         print(res)
                    #         continue
                    #
                    #     except Exception as e:
                    #         print("连接关闭，正在重连……")
                    #         break

                    except Exception as e:
                        # 这里好像没有完全退出
                        LOGGING.error(f"{target_stock}，连接断开，不重新连接，请检查……其他 {e}")
                        break

        # 重新尝试连接，使用指数退避策略
        except websockets.exceptions.ConnectionClosed as e:
            reconnect_attempts += 1
            wait_time = min(2 ** reconnect_attempts, 60)  # 最大等待时间为60秒
            LOGGING.info(f"Connection closed: {e}\n Reconnecting in {wait_time} seconds...")
            await asyncio.sleep(wait_time)

        except asyncio.TimeoutError:
            print("Timeout reading from socket.")
            reconnect_attempts += 1
            wait_time = min(2 ** reconnect_attempts, 60)  # 最大等待时间为60秒
            LOGGING.info(f"Connection closed: {e}\n Reconnecting in {wait_time} seconds...")
            await asyncio.sleep(wait_time)

        # 重新尝试连接，使用指数退避策略,针对于“远程计算机拒绝网络连接”错误
        except socket.error as e:
            reconnect_attempts += 1
            wait_time = min(2 ** reconnect_attempts, 60)  # 最大等待时间为60秒
            LOGGING.info(f"Connection closed: {e}\n Reconnecting in {wait_time} seconds...")
            await asyncio.sleep(wait_time)

        except Exception as e:
            LOGGING.info(f'连接断开，不重新连接，请检查……其他: {e}')
            if "Timeout reading from socket" in str(e):
                LOGGING.info("Timeout , and reconnecting")
                time.sleep(10)
                continue
            if "sbsb" in str(e):
                LOGGING.info("Timeout , and reconnecting")
                time.sleep(10)
                continue
            if "pymysql.err.OperationalError" in str(e):  # 应对mysql连接断开
                LOGGING.info("Timeout , and reconnecting")
                time.sleep(10)
                continue
            break
            
        finally:
            LOGGING.error(f"出错股票: {target_stock} !!!!")


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
