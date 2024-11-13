import json
import time
import hmac
import hashlib
import base64
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
                response = await websocket.recv()
                print("收到增量数据: ", response)

                # 如果需要处理消息，可以在这里添加逻辑
            except websockets.exceptions.ConnectionClosedOK:
                print("over")


if __name__ == '__main__':


    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())