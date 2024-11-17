import json
import time
import hmac
import hashlib
import base64
import socket
from datetime import datetime
import asyncio

import websockets

# 指定.env.dev文件的路径
from pathlib import Path
from dotenv import load_dotenv

project_path = Path(__file__).resolve().parent  # 此脚本的运行"绝对"路径
import os

dotenv_path = os.path.join(project_path, '../.env.dev')

# 载入环境变量
load_dotenv(dotenv_path)
api_key = os.getenv('API_KEY')
secret_key = os.getenv('SECRET_KEY')
passphrase = os.getenv('PASSPHRASE')



timestamp = int(time.time())
print("timestamp: " + str(timestamp))
sign = str(timestamp) + 'GET' + '/users/self/verify'
total_params = bytes(sign, encoding= 'utf-8')
signature = hmac.new(bytes(secret_key, encoding= 'utf-8'), total_params, digestmod=hashlib.sha256).digest()
signature = base64.b64encode(signature)
signature = str(signature, 'utf-8')

print("signature = {0}".format(signature))

target_stock = "FLOKI-USDT"


def account(result):
    """账户信息"""
    print("\n")

    data = result['data'][0]['balData']
    print("=====================资金用户===========================")
    # totalEq = round(float(totalEq), 2)
    # print(f'总资产: {totalEq} 美元')

    for item in data:
        currency = item['ccy']
        cashBal = round(float(item['cashBal']), 2)

        # print(f"{currency}, 权益: {cashBal}, 现价: {eqUsd} USDT")
        print(f"{currency}, 权益: {cashBal}")


async def main():
    msg = {
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
                print("发送登录消息: ", msg)
                await websocket.send(json.dumps(msg))

                # 接收并打印登录响应
                response = await websocket.recv()
                print("登录响应: ", response)

                # 发送订阅请求
                await websocket.send(json.dumps(subscribe_msg))
                subscribe_response = await websocket.recv()
                print("订阅响应: ", subscribe_response)

                # 持续监听增量数据
                while True:
                    try:
                        # response = await websocket.recv()
                        response = await asyncio.wait_for(websocket.recv(), timeout=25)

                        # print("收到增量数据: ", response)
                        response = json.loads(response)
                        if response.get("data"):
                            account(response)

                    except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed) as e:
                        try:
                            await websocket.send('ping')
                            res = await websocket.recv()
                            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(f"{current_time} 收到: {res}")
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