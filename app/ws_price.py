import asyncio
import websockets
import json

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

target_stock = "FLOKI-USDT"
# target_stock = "BTC-USDT"


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

    async with websockets.connect('wss://ws.okx.com:8443/ws/v5/public') as websocket:
        # 发送订阅请求
        await websocket.send(json.dumps(subscribe_msg))
        subscribe_response = await websocket.recv()
        print("订阅响应: ", subscribe_response)

        # 持续监听增量数据
        while True:
            try:
                response = await websocket.recv()
                # print("收到增量数据: ", response)
                # 将字符串转换为字典
                data_dict = json.loads(response)
                # 打印转换后的字典
                os.system("clear")
                price = data_dict["data"][0]["px"]
                num = data_dict["data"][0]["sz"]

                print(f"标的:{target_stock}")
                print(f"成交价格:{price}")
                print(f"成交数量:{num}")

                # 如果需要处理消息，可以在这里添加逻辑
            except websockets.exceptions.ConnectionClosedOK:
                print("over")


if __name__ == '__main__':


    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())