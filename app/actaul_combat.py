import asyncio
import datetime
from datetime import datetime
import socket
import time
import hmac
import hashlib
import base64
import websockets
import json
import redis

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

ATR = 999999
HISTORY_MAX_PRICE = 999999
HISTORY_MIN_PRICE = 0
LONG_POSITION = 0


def buy_order(target_stock, amount, price=None):
    timestamp = int(time.time())
    order_type = "limit"
    tgtCcy = ""
    if price is None:
        order_type = "market"
        tgtCcy = "base_ccy"

    sort_name = target_stock.split("-")[0]
    client_order_id = f"{sort_name}{timestamp}"

    order_msg = {
        "op": "order",
        "id": client_order_id,
        "args": [
            {
                "ordType": order_type,
                "instId": target_stock,
                "clOrdId": client_order_id,
                "tgtCcy": tgtCcy,
                "sz": str(amount),
                "px": str(price),
                "tdMode": "cash",
                "side": "buy",
            }
        ]
    }

    return order_msg, client_order_id


def sell_order(target_stock, amount, price=None):
    timestamp = int(time.time())
    order_type = "limit"
    if price is None:
        order_type = "market"

    sort_name = target_stock.split("-")[0]
    client_order_id = f"{sort_name}{timestamp}"

    order_msg = {
        "op": "order",
        "id": client_order_id,
        "args": [
            {
                "ordType": order_type,
                "instId": target_stock,
                "clOrdId": client_order_id,
                # "tgtCcy": tgtCcy,
                "sz": str(amount),
                "px": str(price),
                "tdMode": "cash",
                "side": "sell",
            }
        ]
    }

    return order_msg, client_order_id


# 生成订单消息
def create_order(target_stock, amount, side, price=None):
    timestamp = int(time.time())
    order_type = "limit" if price else "market"
    client_order_id = f"{target_stock.split('-')[0]}{timestamp}"

    order_msg = {
        "op": "order",
        "id": client_order_id,
        "args": [
            {
                "ordType": order_type,
                "instId": target_stock,
                "clOrdId": client_order_id,
                "tgtCcy": "" if order_type == "limit" else "base_ccy",
                "sz": str(amount),
                "px": str(price) if price else None,
                "tdMode": "cash",
                "side": side,
            }
        ]
    }
    return order_msg, client_order_id


def prepare_login():
    timestamp = int(time.time())
    print("timestamp: " + str(timestamp))
    sign = str(timestamp) + 'GET' + '/users/self/verify'
    total_params = bytes(sign, encoding='utf-8')
    signature = hmac.new(bytes(secret_key, encoding='utf-8'), total_params, digestmod=hashlib.sha256).digest()
    signature = base64.b64encode(signature)
    signature = str(signature, 'utf-8')
    print("signature = {0}".format(signature))

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


def update_reference_index(target_stock):
    from module.redis_url import redis_url
    redis_okx = redis.Redis.from_url(redis_url)

    # 获取单个字段的值
    name = redis_okx.hget(f"stock:{target_stock}", 'update_time')
    if name is None:
        return 0
    name = name.decode()
    print(name)

    # 获取整个哈希表的所有字段和值
    all_info = redis_okx.hgetall(f"stock:{target_stock}")

    # 解码每个键和值
    decoded_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in all_info.items()}
    # print(decoded_data)

    history_max_price, history_min_price = float(decoded_data['history_max_price']), float(
        decoded_data['history_min_price'])
    atr = float(decoded_data['ATR'])
    print(atr)
    print(history_max_price)
    print(history_min_price)

    global ATR, HISTORY_MAX_PRICE, HISTORY_MIN_PRICE
    ATR, HISTORY_MAX_PRICE, HISTORY_MIN_PRICE = atr, history_max_price, history_min_price

    return 1


async def handle_private_connection(target_stock, amount, side):
    account_msg = prepare_login()

    # if side == "buy":
    #     order_msg, client_order_id = buy_order(target_stock, amount)
    # else:
    #     order_msg, client_order_id = sell_order(target_stock, amount)
    order_msg, client_order_id = create_order(target_stock, amount, side, price=None)
    print(order_msg)

    async with websockets.connect('wss://ws.okx.com:8443/ws/v5/private') as websocket:
        print("发送登录消息: ", account_msg)
        await websocket.send(json.dumps(account_msg))
        response = await websocket.recv()
        print("登录响应: ", response)

        # 发送订单
        await websocket.send(json.dumps(order_msg))
        subscribe_response = await websocket.recv()
        print("订阅响应: ", subscribe_response)
        data_dict = json.loads(response)
        print(data_dict)

        # 手动关闭连接（虽然 async with 会自动关闭，但可以显示调用关闭）
        await websocket.close()


async def main():
    global LONG_POSITION

    ssb = 1

    # target_stock = "FLOKI-USDT"
    # target_stock = "OMI-USDT"
    target_stock = "LUNC-USDT"
    amount = 10030

    # 订阅产品频道的消息
    subscribe_msg = {
        "op": "subscribe",
        "args": [
            {
                "channel": "trades",
                "instId": target_stock
            }
        ]
    }
    while True:
        reconnect_attempts = 0

        # 更新震荡参数
        flag_exit = update_reference_index(target_stock)
        if not flag_exit:
            print("index_not_exist!!!!")
            break

        try:
            bj_tz = datetime.timezone(datetime.timedelta(hours=8))
            async with websockets.connect('wss://ws.okx.com:8443/ws/v5/public') as websocket:
                # 发送订阅请求
                await websocket.send(json.dumps(subscribe_msg))
                subscribe_response = await websocket.recv()
                print("订阅响应: ", subscribe_response)

                # 持续监听增量数据
                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=25)
                        data_dict = json.loads(response)
                        price = data_dict["data"][0]["px"]
                        num = data_dict["data"][0]["sz"]

                        print(f"标的:{target_stock}")
                        print(f"成交价格:{price}")
                        print(f"成交数量:{num}")

                        now_bj = datetime.datetime.now(bj_tz)
                        if now_bj.hour == 8 and now_bj.minute == 1 and now_bj.second < 10:
                            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            print(f"到点了 :{current_time} ")
                            # update_reference_index(target_stock)

                        # # 建仓完成
                        # if float(price) >= HISTORY_MAX_PRICE and ssb > 0:
                        #     ssb -= 1
                        #     asyncio.create_task(handle_private_connection(target_stock, amount,"buy"))
                        #     LONG_POSITION+=1
                        #
                        # if float(price) >= HISTORY_MAX_PRICE+LONG_POSITION*0.5*ATR and LONG_POSITION <= 4:
                        #     asyncio.create_task(handle_private_connection(target_stock, amount,"buy"))
                        #     LONG_POSITION+=1
                        #
                        #
                        # if float(price) <= HISTORY_MIN_PRICE:
                        #     asyncio.create_task(handle_private_connection(target_stock, amount,"sell"))


                    except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed) as e:
                        # 超过25s了
                        try:
                            await websocket.send('ping')
                            res = await websocket.recv()
                            print(res)
                            continue

                        except Exception as e:
                            print("连接关闭，正在重连……")
                            print(e)
                            break

        # 重新尝试连接，使用指数退避策略
        except websockets.exceptions.ConnectionClosed as e:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            reconnect_attempts += 1
            wait_time = min(2 ** reconnect_attempts, 60)  # 最大等待时间为60秒
            print(f"{current_time} Reconnecting in {wait_time} seconds...")
            print(f"Connection closed: {e}")
            await asyncio.sleep(wait_time)

        # 重新尝试连接，使用指数退避策略,针对于“远程计算机拒绝网络连接”错误
        except socket.error as e:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            reconnect_attempts += 1
            wait_time = min(2 ** reconnect_attempts, 60)  # 最大等待时间为60秒
            print(f"{current_time} Reconnecting in {wait_time} seconds...")
            print(f"Connection closed: {e}")
            await asyncio.sleep(wait_time)

        except Exception as e:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{current_time} 连接断开，正在重连……")
            print('其他', e)


if __name__ == '__main__':
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(main())

    print(ATR)

    target_stock = "LUNC-USDT"
    flag_exit = update_reference_index(target_stock)
    if not flag_exit:
        print("index_not_exist!!!!")

    print(ATR)
