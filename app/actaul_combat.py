import asyncio
# import datetime
from datetime import datetime, timezone, timedelta
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


import logging.config
from utils.logging_config import Logging_dict

logging.config.dictConfig(Logging_dict)
LOGGING = logging.getLogger("app_01")


# class LOGGING:
#     @staticmethod
#     def info(message):
#         LOGGING.info(message)


from MsgSender.wx_msg import send_wx_info

ATR = 999999
up_Dochian_price = 999999
down_Dochian_price = 0
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


def update_reference_index(target_stock):
    from module.redis_url import redis_url
    redis_okx = redis.Redis.from_url(redis_url)

    # 获取单个字段的值
    name = redis_okx.hget(f"stock:{target_stock}", 'update_time')
    if name is None:
        return 0
    name = name.decode()
    LOGGING.info("开始更新每日参数")
    LOGGING.info(f"参数更新的最后日期: {name}")

    # 获取整个哈希表的所有字段和值
    all_info = redis_okx.hgetall(f"stock:{target_stock}")

    # 解码每个键和值
    decoded_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in all_info.items()}
    # LOGGING.info(decoded_data)

    history_max_price, history_min_price = float(decoded_data['history_max_price']), float(
        decoded_data['history_min_price'])
    atr = float(decoded_data['ATR'])
    LOGGING.info(atr)
    LOGGING.info(history_max_price)
    LOGGING.info(history_min_price)

    global ATR, up_Dochian_price, down_Dochian_price
    ATR, up_Dochian_price, down_Dochian_price = atr, history_max_price, history_min_price

    return 1


def contrast_range(now_price, target_market_price):
    # 计算目标价格的1%
    one_percent = target_market_price * 0.01

    # 计算目标价格的上下限
    lower_bound = target_market_price - one_percent
    upper_bound = target_market_price + one_percent

    # 检查当前价格是否在目标价格的±1%范围内
    if lower_bound <= now_price <= upper_bound:
        return True
    else:
        return False

async def handle_private_connection(target_stock, amount, side):
    account_msg = prepare_login()

    # if side == "buy":
    #     order_msg, client_order_id = buy_order(target_stock, amount)
    # else:
    #     order_msg, client_order_id = sell_order(target_stock, amount)
    order_msg, client_order_id = create_order(target_stock, amount, side, price=None)
    LOGGING.info(order_msg)

    async with websockets.connect('wss://ws.okx.com:8443/ws/v5/private') as websocket:
        LOGGING.info(f"发送登录消息: {account_msg}")
        await websocket.send(json.dumps(account_msg))
        response = await websocket.recv()
        LOGGING.info(f"登录响应: {response}")
        data_dict = json.loads(response)
        LOGGING.info(data_dict)

        # 发送订单
        await websocket.send(json.dumps(order_msg))
        subscribe_response = await websocket.recv()
        LOGGING.info(f"订阅响应: {subscribe_response}")

        # 手动关闭连接（虽然 async with 会自动关闭，但可以显示调用关闭）
        await websocket.close()


async def main():
    from simulate_combat import Account_info
    from simulate_combat import sell
    account_info = Account_info()

    global LONG_POSITION


    target_stock = "LUNC-USDT"
    target_stock = "BTC-USDT"
    # target_stock = "FLOKI-USDT"
    # target_stock = "OMI-USDT"
    # target_stock = "DOGE-USDT"
    # target_stock = "PEPE-USDT"


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

    day_li = []

    while True:
        reconnect_attempts = 0
        flag = 0


        # 更新震荡参数
        flag_exit = update_reference_index(target_stock)
        # attributes = account_info.print_all_info()
        # for attr, value in attributes.items():
        #     LOGGING.info(f"{attr}: {value}")
        # LOGGING.info(account_info.balance + account_info.hold_amount * account_info.hold_price)

        if not flag_exit:
            LOGGING.info("index_not_exist!!!!")
            break

        try:
            async with websockets.connect('wss://ws.okx.com:8443/ws/v5/public') as websocket:
                # 发送订阅请求
                await websocket.send(json.dumps(subscribe_msg))
                subscribe_response = await websocket.recv()
                LOGGING.info(f"订阅响应: {subscribe_response}")

                # 持续监听增量数据
                while True:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=20)
                        data_dict = json.loads(response)
                        price = data_dict["data"][0]["px"]
                        num = data_dict["data"][0]["sz"]

                        # LOGGING.info(f"标的:{target_stock}")
                        # LOGGING.info(f"成交价格:{price}")
                        # LOGGING.info(f"成交数量:{num}")

                        bj_tz = timezone(timedelta(hours=8))
                        now_bj = datetime.now().astimezone(bj_tz)
                        # today = now_bj.day  # 当前月份的第几天
                        hour_of_day = now_bj.hour  # 第几时
                        minute = now_bj.minute  # 第几分
                        if hour_of_day == 8 and minute == 1:
                            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                            if current_time not in day_li:
                                flag = 0
                                day_li.append(current_time)
                                LOGGING.info(f"到点了 :{current_time} ")
                                res = send_wx_info("更新策略参数", f"{current_time}", supreme_auth=True)
                                LOGGING.info(res)

                                # 打印账户信息
                                attributes = account_info.print_all_info()
                                for attr, value in attributes.items():
                                    LOGGING.info(f"{attr}: {value}")
                                LOGGING.info(account_info.balance + account_info.hold_amount * account_info.hold_price)

                                # update_reference_index(target_stock)

                        now_price = float(price)
                        today_timestamp = int(time.time())

                        position = account_info.long_position
                        target_market_price = up_Dochian_price
                        if contrast_range(now_price, target_market_price) and position == 0:
                            LOGGING.info("建仓")
                            flag = 1
                            # buy_days.append([today_timestamp, target_market_price])

                            amount = round(account_info.risk_rate * account_info.init_balance / ATR, 5)
                            LOGGING.info(f"市场价:{price}")
                            total_cost = amount * target_market_price
                            LOGGING.info(f"amount: {amount}, 目标价price: {target_market_price}")
                            LOGGING.info(f"total_cost: {round(total_cost, 3)}")

                            account_info.update_info(
                                {
                                    "balance": account_info.balance - total_cost,
                                    "init_balance": account_info.balance,
                                    "long_position": position + 1,
                                    "hold_amount": account_info.hold_amount + amount,
                                    "max_hold_amount": account_info.hold_amount + amount,
                                    "hold_price": target_market_price,
                                    "total_cost": account_info.total_cost + total_cost,
                                    "open_price": target_market_price,
                                    "total_ratio": 1.0
                                }
                            )
                            LOGGING.info(f"balance:{round(account_info.balance, 3)}")

                        for _ in range(account_info.max_long_position):
                            position = account_info.long_position
                            target_market_price = round(account_info.open_price + position * 0.5 * ATR, 10)
                            if contrast_range(now_price, target_market_price) and 0 < position <= account_info.max_long_position:
                                LOGGING.info("加仓")
                                flag = 1
                                # buy_days.append([today_timestamp, target_market_price])

                                amount = round(account_info.risk_rate * account_info.init_balance / ATR, 5)
                                now_cost = amount * target_market_price
                                LOGGING.info(f"amount: {amount}, price: {target_market_price}")
                                LOGGING.info(f"total_cost: {round(now_cost, 3)}")

                                account_info.update_info(
                                    {
                                        "balance": account_info.balance - now_cost,
                                        "long_position": position + 1,
                                        "hold_price": target_market_price,
                                        "hold_amount": account_info.hold_amount + amount,
                                        "total_cost": account_info.total_cost + now_cost,
                                        "max_hold_amount": account_info.hold_amount + amount,
                                    }
                                )
                                LOGGING.info(f"balance:{round(account_info.balance, 3)}")

                        for _ in range(account_info.max_sell_times):
                            position = account_info.long_position
                            sell_time = account_info.sell_times
                            target_market_price = round(account_info.open_price + (0.5 * sell_time + 2) * ATR, 10)
                            if contrast_range(now_price, target_market_price) and position > 0:
                                LOGGING.info(f"减仓(+{0.5 * sell_time + 2}N线, 分批止盈)")
                                flag = 1
                                # sell_days.append([today_timestamp, target_market_price])

                                ratio = 0.3 if sell_time <= 1 else 0.2
                                LOGGING.info(f"ratio: {ratio}")
                                sell(account_info, target_market_price, ratio=ratio, today_timestamp=today_timestamp)

                        position = account_info.long_position
                        target_market_price = round(account_info.hold_price + 0.1 * ATR, 10)
                        if contrast_range(now_price, target_market_price) and position > 0 and account_info.sell_times == account_info.max_sell_times and flag == 0:
                            LOGGING.info("减仓(+1.5N线, 追加止盈)")
                            # sell_days.append([today_timestamp, target_market_price])
                            sell(account_info, target_market_price, ratio=0.3, today_timestamp=today_timestamp)

                        position = account_info.long_position
                        if position > 0 and flag == 0:
                            # 除数不为零
                            hold_average_price = (account_info.init_balance - account_info.balance) / account_info.hold_amount
                            target_market_price = round(hold_average_price + 0.5 * ATR, 10)
                            if contrast_range(now_price, target_market_price) and position > 0:
                                LOGGING.info("平仓(+0N线, 动态追踪止损)")
                                flag = 1

                                # sell_empty_days.append([today_timestamp, target_market_price])
                                sell(account_info, target_market_price, today_timestamp=today_timestamp)

                        position = account_info.long_position
                        stop_loss_price = round(account_info.open_price - 0.5 * ATR, 10)
                        target_market_price = max(stop_loss_price, down_Dochian_price)
                        if contrast_range(now_price, target_market_price) and position > 0 and flag == 0:
                            flag = 1
                            LOGGING.info("平仓(max-0.5N线/唐奇安)")
                            LOGGING.info(f"stop_loss: {stop_loss_price}  down:{down_Dochian_price}")

                            # sell_empty_days.append([today_timestamp, target_market_price])
                            sell(account_info, target_market_price, today_timestamp=today_timestamp)


                        position = account_info.long_position
                        stop_loss_price = round(account_info.open_price - 0.5 * ATR, 10)
                        target_market_price = min(stop_loss_price, down_Dochian_price)
                        if contrast_range(now_price, target_market_price) and position > 0 and flag == 0:
                            flag = 1
                            LOGGING.info("平仓(min-0.5N线/唐奇安)")
                            LOGGING.info(f"stop_loss: {stop_loss_price}  down:{down_Dochian_price}")

                            # sell_empty_days.append([today_timestamp, target_market_price])
                            sell(account_info, target_market_price, today_timestamp=today_timestamp)



                    except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed) as e:
                        # 超过25s了
                        try:
                            await websocket.send('ping')
                            res = await websocket.recv()
                            LOGGING.info(res)
                            continue

                        except Exception as e:
                            LOGGING.info(f"连接关闭，正在重连…… {e}")
                            break

        # 重新尝试连接，使用指数退避策略
        except websockets.exceptions.ConnectionClosed as e:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            reconnect_attempts += 1
            wait_time = min(2 ** reconnect_attempts, 60)  # 最大等待时间为60秒
            LOGGING.info(f"{current_time} Reconnecting in {wait_time} seconds...")
            LOGGING.info(f"Connection closed: {e}")
            await asyncio.sleep(wait_time)

        # 重新尝试连接，使用指数退避策略,针对于“远程计算机拒绝网络连接”错误
        except socket.error as e:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            reconnect_attempts += 1
            wait_time = min(2 ** reconnect_attempts, 60)  # 最大等待时间为60秒
            LOGGING.info(f"{current_time} Reconnecting in {wait_time} seconds...")
            LOGGING.info(f"Connection closed: {e}")
            await asyncio.sleep(wait_time)

        except Exception as e:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            LOGGING.info(f"{current_time} 连接断开，正在重连……")
            LOGGING.info(f'其他 {e}')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())


    # result = contrast_range(99.005, 100)
    # LOGGING.info(result)

    # LOGGING.info(ATR)
    #
    # target_stock = "LUNC-USDT"
    # flag_exit = update_reference_index(target_stock)
    # if not flag_exit:
    #     LOGGING.info("index_not_exist!!!!")
    #
    # LOGGING.info(ATR)
