import json
import socket
import redis
from datetime import datetime, timezone, timedelta

import asyncio
import websockets

from MsgSender.wx_msg import send_wx_info
from MsgSender.feishu_msg import send_feishu_info
from monitor.monitor_account import check_state
from monitor.monitor_account import prepare_login

import logging.config
from utils.logging_config import Logging_dict

logging.config.dictConfig(Logging_dict)
LOGGING = logging.getLogger("auto_sync_account")

# 订阅账户频道的消息
subscribe_msg = {
    "op": "subscribe",
    "args": [
        {
            "channel": "balance_and_position",
        }
    ]
}

target_stock_li = [
    "BTC-USDT",
    "ETH-USDT",
    "DOGE-USDT",
    "FLOKI-USDT",
    # "LUNC-USDT",
    # "OMI-USDT",
    # "PEPE-USDT",
]


def update_chain(result):
    data = result['data'][0]['balData']

    for item in data:
        currency = item['ccy']
        hold_stock = currency + "-USDT"
        # LOGGING.info(hold_stock)

        if hold_stock in target_stock_li:
            check_state(hold_stock)


async def main():
    while True:
        reconnect_attempts = 0
        try:
            async with websockets.connect('wss://ws.okx.com:8443/ws/v5/private') as websocket:
                account_msg = prepare_login()
                LOGGING.info(f"发送登录消息: {account_msg}")
                await websocket.send(json.dumps(account_msg))
                response = await websocket.recv()
                LOGGING.info(f"登录响应: {response}")

                # 发送订阅请求
                await websocket.send(json.dumps(subscribe_msg))
                subscribe_response = await websocket.recv()
                LOGGING.info(f"订阅响应: {subscribe_response}")

                # 持续监听增量数据
                while True:
                    try:
                        # response = await websocket.recv()
                        response = await asyncio.wait_for(websocket.recv(), timeout=25)

                        LOGGING.info(f"收到增量数据: {response}")
                        response = json.loads(response)
                        if response.get("data"):
                            update_chain(response)

                    except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed) as e:
                        try:
                            await websocket.send('ping')
                            res = await websocket.recv()
                            LOGGING.info(f"收到: {res}")
                            continue

                        except Exception as e:
                            LOGGING.info(f"连接关闭，正在重连…… {e}")
                            break

        # 重新尝试连接，使用指数退避策略
        except websockets.exceptions.ConnectionClosed as e:
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
            LOGGING.error(f"连接断开，不重新连接，请检查……其他 {e}")
            break


if __name__ == '__main__':
    # 争对此问题！！！
    # 连接断开，不重新连接，请检查……其他 timed out during handshake

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
