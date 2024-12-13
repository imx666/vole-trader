import json
import time
import hmac
import hashlib
import base64
import socket
from datetime import datetime
import asyncio
import os
import websockets

from pathlib import Path
from dotenv import load_dotenv

project_path = Path(__file__).resolve().parent  # 此脚本的运行"绝对"路径
# project_path = os.getcwd()  # 此脚本的运行的"启动"路径
dotenv_path = os.path.join(project_path, '../.env.dev')  # 指定.env.dev文件的路径
load_dotenv(dotenv_path)  # 载入环境变量

api_key = os.getenv('API_KEY')
secret_key = os.getenv('SECRET_KEY')
passphrase = os.getenv('PASSPHRASE')



import logging.config
from utils.logging_config import Logging_dict

logging.config.dictConfig(Logging_dict)
LOGGING = logging.getLogger("app_01")

from MsgSender.wx_msg import send_wx_info


def show_account(result):
    """账户信息"""
    LOGGING.info("\n")

    data = result['data'][0]['balData']
    LOGGING.info("=====================资金用户===========================")
    # totalEq = round(float(totalEq), 2)
    # LOGGING.info(f'总资产: {totalEq} 美元')

    title = "账户更新"
    content = f"<font color=\"warning\">{title}</font>"
    for item in data:
        currency = item['ccy']
        cashBal = round(float(item['cashBal']), 8)

        # LOGGING.info(f"{currency}, 权益: {cashBal}, 现价: {eqUsd} USDT")
        LOGGING.info(f"{currency}, 权益: {cashBal}")
        content += f"\n>{currency}<font color=\"comment\">权益: {cashBal}</font>"

    custom_dict = {
        "msgtype": "markdown",
        "markdown": {
            "content": content
        }
    }

    if len(data) <= 2:
        res = send_wx_info(1, 1, custom=custom_dict, supreme_auth=True)
        LOGGING.info(res)


def prepare_login():
    timestamp = int(time.time())
    LOGGING.info(f"timestamp: {str(timestamp)}")
    sign = str(timestamp) + 'GET' + '/users/self/verify'
    total_params = bytes(sign, encoding='utf-8')
    signature = hmac.new(bytes(secret_key, encoding='utf-8'), total_params, digestmod=hashlib.sha256).digest()
    signature = base64.b64encode(signature)
    signature = str(signature, 'utf-8')
    LOGGING.info(f"signature = {signature}")

    account_msg = {
        "op": "login",
        "args": [
            {
                "apiKey": f'{api_key}',
                "passphrase": f'{passphrase}',
                "timestamp": f'{timestamp}',
                "sign": f'{signature}'
            }
        ]
    }

    return account_msg


async def main():
    # 订阅账户频道的消息
    subscribe_msg = {
        "op": "subscribe",
        "args": [
            {
                "channel": "balance_and_position",
            }
        ]
    }
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
                            show_account(response)

                    except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed) as e:
                        try:
                            await websocket.send('ping')
                            res = await websocket.recv()
                            LOGGING.info(res)
                            # current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            # LOGGING.info(f"{current_time} 收到: {res}")
                            continue

                        except Exception as e:
                            LOGGING.info(f"连接关闭，正在重连…… {e}")
                            break

        # 重新尝试连接，使用指数退避策略
        except websockets.exceptions.ConnectionClosed as e:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            reconnect_attempts += 1
            wait_time = min(2 ** reconnect_attempts, 60)  # 最大等待时间为60秒
            LOGGING.error(f"{current_time} Reconnecting in {wait_time} seconds...")
            LOGGING.error(f"Connection closed: {e}")
            await asyncio.sleep(wait_time)

        # 重新尝试连接，使用指数退避策略,针对于“远程计算机拒绝网络连接”错误
        except socket.error as e:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            reconnect_attempts += 1
            wait_time = min(2 ** reconnect_attempts, 60)  # 最大等待时间为60秒
            LOGGING.error(f"{current_time} Reconnecting in {wait_time} seconds...")
            LOGGING.error(f"Connection closed: {e}")
            await asyncio.sleep(wait_time)

        except Exception as e:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            LOGGING.error(f"{current_time} 连接断开，正在重连……")
            LOGGING.error(f'其他 {e}')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
