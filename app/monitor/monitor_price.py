import asyncio
from datetime import datetime
import socket

import websockets
import json


import logging.config
from utils.logging_config import Logging_dict

logging.config.dictConfig(Logging_dict)
LOGGING = logging.getLogger(f"VoleTrader")



# target_stock = "FLOKI-USDT"
target_stock = "BTC-USDT"


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

                        # print("收到增量数据: ", response)
                        # 将字符串转换为字典
                        data_dict = json.loads(response)
                        # os.system("clear")
                        # price = data_dict["data"][0]["px"]
                        # num = data_dict["data"][0]["sz"]

                        # print(f"标的:{target_stock}")
                        # print(f"成交价格:{price}")
                        # print(f"成交数量:{num}")
                        now_price = float(data_dict["data"][0]["px"])

                        LOGGING.info(f"now_price: {now_price}")

                    except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed) as e:
                        try:
                            await websocket.send('ping')
                            res = await websocket.recv()
                            print(res)
                            continue

                        except Exception as e:
                            print("连接关闭，正在重连……")
                            break


        except websockets.exceptions.InvalidURI as e:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{current_time} 连接断开，正在重连……")
            print('uri异常！')
            await asyncio.sleep(5)  # 等待5秒后重试

        # 重新尝试连接，使用指数退避策略
        except websockets.exceptions.ConnectionClosed as e:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{current_time} 连接断开，正在重连……")
            print(f"Connection closed: {e}")
            reconnect_attempts += 1
            wait_time = min(2 ** reconnect_attempts, 60)  # 最大等待时间为60秒
            print(f"Reconnecting in {wait_time} seconds...")
            await asyncio.sleep(wait_time)

        # 重新尝试连接，使用指数退避策略,针对于“远程计算机拒绝网络连接”错误
        except socket.error as e:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{current_time} 连接断开，正在重连……")
            print(f"Connection closed: {e}")
            reconnect_attempts += 1
            wait_time = min(2 ** reconnect_attempts, 60)  # 最大等待时间为60秒
            print(f"Reconnecting in {wait_time} seconds...")
            await asyncio.sleep(wait_time)

        except Exception as e:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{current_time} 连接断开，正在重连……")
            print('其他', e)



if __name__ == '__main__':


    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())