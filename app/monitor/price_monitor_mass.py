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
LOGGING = logging.getLogger(f"price_monitor")



target_stock_li = [
  "FLOKI-USDT",
  "LUNC-USDT",
  "OMI-USDT",
  "ZRX-USDT",
  "RACA-USDT",
  "JST-USDT",
  "ZIL-USDT",
  "ORDI-USDT",
]

args_li = []
for stock in target_stock_li:
    arg = {
            "channel": "trades",
            "instId": stock
        }
    args_li.append(arg)

# 订阅产品频道的消息
subscribe_msg = {
    "op": "subscribe",
    "args": args_li
}

# # 订阅产品频道的消息
# subscribe_msg = {
#     "op": "subscribe",
#     "args": [
#         {
#             "channel": "trades",
#             "instId": target_stock_li[0]
#         },
#         {
#             "channel": "trades",
#             "instId": target_stock_li[3]
#         }
#     ]
# }

from utils.url_center import redis_url_fastest
redis_fastest = redis.Redis.from_url(redis_url_fastest)


def update_real_time_info(target_stock, now_price, trading_volume):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamp_seconds = time.time()
    timestamp_ms = int(timestamp_seconds * 1000)  # 转换为毫秒
    redis_fastest.hset(f"real_time_index:{target_stock}",
                       mapping={
                           'now_price': now_price,
                           'trading_volume': trading_volume,
                           'update_time': timestamp_ms,
                           'update_time(24时制)': current_time,
                       })


async def main():
    reconnect_attempts = 0
    cankao_data = None
    while True:
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
                        response = await asyncio.wait_for(websocket.recv(), timeout=5)
                        cankao_data = response
                        if cankao_data == "pong":
                            continue
                        data_dict = json.loads(response)
                        if "event" in data_dict.keys():
                            LOGGING.info(f"订阅响应: {data_dict}")
                            continue
                        target_stock = data_dict["data"][0]["instId"]
                        now_price = float(data_dict["data"][0]["px"])
                        trading_volume = float(data_dict["data"][0]["sz"])
                        # print(data_dict)

                        # LOGGING.info(f"now_price: {now_price}")
                        update_real_time_info(target_stock, now_price, trading_volume)
                    except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed) as e:
                        try:
                            await websocket.send('ping')
                            await websocket.recv()
                            # res = await websocket.recv()
                            # LOGGING.warning(f"{target_stock}收到: {res}")
                            continue

                        except Exception as e:
                            LOGGING.error(f"{target_stock_li}连接关闭，正在重连…… {e}")
                            break

        # 重新尝试连接，使用指数退避策略
        except websockets.exceptions.ConnectionClosed as e:
            reconnect_attempts += 1
            wait_time = min(2 ** reconnect_attempts, 60)  # 最大等待时间为60秒
            LOGGING.info(f"Connection closed: {e}\n Reconnecting in {wait_time} seconds...")
            await asyncio.sleep(wait_time)
            continue

        except asyncio.TimeoutError as e:
            LOGGING.error("3333 Timeout reading from socket.")
            reconnect_attempts += 1
            wait_time = min(2 ** reconnect_attempts, 60)  # 最大等待时间为60秒
            LOGGING.info(f"Connection closed: {e}\n Reconnecting in {wait_time} seconds...")
            await asyncio.sleep(wait_time)
            continue

        # 重新尝试连接，使用指数退避策略,针对于“远程计算机拒绝网络连接”错误
        except socket.error as e:
            reconnect_attempts += 1
            wait_time = min(2 ** reconnect_attempts, 60)  # 最大等待时间为60秒
            LOGGING.error(f"Connection closed: {e}\n Reconnecting in {wait_time} seconds...")
            await asyncio.sleep(wait_time)
            continue

        except Exception as e:
            LOGGING.info(f'连接断开，不重新连接，请检查……其他: {e}....{cankao_data}')
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

            # 直接终止
            sys.exit(1)
            # break

        finally:
            LOGGING.error(f"出错股票: {target_stock} !!!!")


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
