import json
import time
import hmac
import hashlib
import base64
import socket
import redis
from datetime import datetime, timezone, timedelta

import asyncio
import os
import websockets

from pathlib import Path
from dotenv import load_dotenv

project_path = Path(__file__).resolve().parent  # 此脚本的运行"绝对"路径
# project_path = os.getcwd()  # 此脚本的运行的"启动"路径
dotenv_path = os.path.join(project_path, '../.env.dev')  # 指定.env.dev文件的路径
print(project_path)
load_dotenv(dotenv_path)  # 载入环境变量

api_key = os.getenv('API_KEY')
secret_key = os.getenv('SECRET_KEY')
passphrase = os.getenv('PASSPHRASE')



import logging.config
from utils.logging_config import Logging_dict

logging.config.dictConfig(Logging_dict)
LOGGING = logging.getLogger("app_01")

from MsgSender.wx_msg import send_wx_info
from module.redis_url import redis_url
from module.genius_trading import GeniusTrader
from module.trade_records import TradeRecordManager


ATR = 999999
up_Dochian_price = 999999
down_Dochian_price = 0




def update_hold_info(target_stock, key, value):
    redis_okx = redis.Redis.from_url(redis_url)
    redis_okx.hset(f"hold_info:{target_stock}", key, value)



def get_hold_info(target_stock):
    redis_okx = redis.Redis.from_url(redis_url)
    # 获取整个哈希表的所有字段和值
    all_info = redis_okx.hgetall(f"hold_info:{target_stock}")

    # 解码每个键和值
    # decoded_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in all_info.items()}
    decoded_data = {k.decode('utf-8'): float(v.decode('utf-8')) for k, v in all_info.items()}
    for attr, value in decoded_data.items():
        print(f"{attr}: {value}")

    # LOGGING.info(decoded_data)
    return decoded_data


def show_time(msg, target_market_price, buyLmt, sellLmt):
    LOGGING.info(msg)
    LOGGING.info(f"target_market_price: {target_market_price}")
    LOGGING.info(f"buyLmt: {buyLmt}, sellLmt: {sellLmt}")

def actual_sell(manager, execution_cycle, ratio, genius_trader, target_stock, target_market_price):
    total_max_amount = manager.get(execution_cycle, "total_max_amount")
    target_amount = round(total_max_amount * ratio, 3)
    rest_amount = manager.get(execution_cycle, "rest_amount")
    amount = rest_amount if rest_amount < target_amount else target_amount
    operation = "close" if rest_amount < target_amount else "reduce"
    # print(amount)

    client_order_id, timestamp_ms = genius_trader.sell_order(target_stock, amount=amount, price=target_market_price)

    # 添加一条新记录
    manager.add_trade_record(
        create_time=datetime.fromtimestamp(timestamp_ms / 1000.0),
        execution_cycle=manager.generate_execution_cycle(strategy_name),
        target_stock=target_stock,
        operation=operation,
        client_order_id=client_order_id,
        price=target_market_price,
        amount=amount,
        value=round(target_market_price * amount, 3),
    )





def update_reference_index(target_stock):
    redis_okx = redis.Redis.from_url(redis_url)

    # 获取单个字段的值
    name = redis_okx.hget(f"common_index:{target_stock}", 'update_time')
    if name is None:
        return 0
    name = name.decode()
    LOGGING.info("开始更新每日参数")
    LOGGING.info(f"参数更新的最后日期: {name}")

    # 获取整个哈希表的所有字段和值
    all_info = redis_okx.hgetall(f"common_index:{target_stock}")

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

    day_li = []
    hold_info = get_hold_info(target_stock)
    genius_trader = GeniusTrader()
    manager = TradeRecordManager(target_stock, strategy_name)


    while True:
        reconnect_attempts = 0

        # 更新震荡参数
        flag_exit = update_reference_index(target_stock)
        if not flag_exit:
            LOGGING.info("index_not_exist!!!!")
            break

        try:
            async with websockets.connect('wss://ws.okx.com:8443/ws/v5/public') as websocket:
                # account_msg = prepare_login()
                # LOGGING.info(f"发送登录消息: {account_msg}")
                # await websocket.send(json.dumps(account_msg))
                # response = await websocket.recv()
                # LOGGING.info(f"登录响应: {response}")

                # 发送订阅请求
                await websocket.send(json.dumps(subscribe_msg))
                subscribe_response = await websocket.recv()
                LOGGING.info(f"订阅响应: {subscribe_response}")

                # 持续监听增量数据
                while True:
                    try:
                        bj_tz = timezone(timedelta(hours=8))
                        now_bj = datetime.now().astimezone(bj_tz)
                        # today = now_bj.day  # 当前月份的第几天
                        hour_of_day = now_bj.hour  # 第几时
                        minute = now_bj.minute  # 第几分


                        if hour_of_day == 8 and minute == 1:
                            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                            if current_time in day_li:
                                continue

                            flag = 0
                            # if current_time not in day_li:
                            update_reference_index(target_stock)
                            day_li.append(current_time)
                            LOGGING.info(f"到点了 :{current_time} ")
                            res = send_wx_info("更新策略参数", f"{current_time}", supreme_auth=True)
                            LOGGING.info(res)

                            # 查询未成交订单并取消
                            record_list = manager.filter_record(state="live")
                            if record_list:
                                for client_order_id in record_list:
                                    result = genius_trader.execution_result(client_order_id=client_order_id)
                                    LOGGING.info(result)
                                    deal_data = result['data'][0]
                                    price_str = deal_data["fillPx"] if deal_data["ordType"] == "market" else deal_data["px"]
                                    state = deal_data["state"]
                                    price = float(price_str)
                                    amount = float(deal_data["sz"])
                                    if state == "filled":  # 已成交,但是部分成交怎么办啊啊啊！！！！！
                                        fill_time = int(deal_data["fillTime"])
                                        manager.update_trade_record(
                                            client_order_id,
                                            state=state,
                                            price=price,
                                            value=round(amount * price, 3),
                                            fill_time=datetime.fromtimestamp(fill_time / 1000.0),
                                        )
                                    else:
                                        genius_trader.cancel_order(target_stock, client_order_id=client_order_id)
                                        manager.update_trade_record(client_order_id, state="canceled")



                        # response = await websocket.recv()
                        response = await asyncio.wait_for(websocket.recv(), timeout=25)
                        # LOGGING.info(f"收到增量数据: {response}")
                        data_dict = json.loads(response)
                        buyLmt = float(data_dict["data"][0]["buyLmt"])
                        sellLmt = float(data_dict["data"][0]["sellLmt"])
                        LOGGING.info(f"buyLmt: {buyLmt}, sellLmt: {sellLmt}")

                        execution_cycle = manager.last_execution_cycle(strategy_name)  # 获取编号
                        long_position = manager.get(execution_cycle, "long_position")
                        target_market_price = up_Dochian_price
                        print(111)
                        if target_market_price < buyLmt and long_position == 0:
                            flag = 1
                            execution_cycle = manager.generate_execution_cycle(strategy_name)  # 生成新编号
                            show_time("建仓", target_market_price, buyLmt, sellLmt)

                            amount = round(hold_info.get("risk_rate") * hold_info.get("init_balance") / ATR, 5)
                            client_order_id, timestamp_ms = genius_trader.buy_order(target_stock, amount=amount, price=target_market_price)

                            # 添加一条新记录
                            manager.add_trade_record(
                                create_time=datetime.fromtimestamp(timestamp_ms / 1000.0),
                                execution_cycle=execution_cycle,
                                operation="build",
                                client_order_id=client_order_id,
                                price=target_market_price,
                                amount=amount,
                                value=round(amount * target_market_price, 3),
                            )

                        long_position = manager.get(execution_cycle, "long_position")
                        print(222)
                        if 0 < long_position <= hold_info.get("max_long_position"):
                            open_price = manager.get(execution_cycle, "open_price")
                            target_market_price = round(open_price + long_position * 0.5 * ATR, 10)
                            if target_market_price < buyLmt:
                                flag = 1
                                show_time("加仓", target_market_price, buyLmt, sellLmt)

                                amount = round(hold_info.get("risk_rate") * hold_info.get("init_balance") / ATR, 5)
                                client_order_id, timestamp_ms = genius_trader.buy_order(target_stock, amount=amount, price=target_market_price)

                                # 添加一条新记录
                                manager.add_trade_record(
                                    create_time=datetime.fromtimestamp(timestamp_ms / 1000.0),
                                    execution_cycle=manager.last_execution_cycle(strategy_name),
                                    operation="add",
                                    client_order_id=client_order_id,
                                    price=target_market_price,
                                    amount=amount,
                                    value=round(amount * target_market_price, 3),
                                )

                        # 卖出
                        long_position = manager.get(execution_cycle, "long_position")
                        print(333)
                        if long_position == 1 + hold_info.get("max_long_position"):
                            open_price = manager.get(execution_cycle, "open_price")
                            sell_times = manager.get(execution_cycle, "sell_times")
                            target_market_price = round(open_price + (0.5 * sell_times + 2) * ATR, 10)
                            if sellLmt < target_market_price and sell_times < hold_info.get("max_sell_times"):
                                msg = f"减仓(+{0.5 * sell_times + 2}N线, 分批止盈)"
                                show_time(msg, target_market_price, buyLmt, sellLmt)

                                ratio = 0.3 if sell_times <= 1 else 0.2
                                actual_sell(manager, execution_cycle, ratio, genius_trader, target_stock, target_market_price)

                            # total_max_amount = manager.get(execution_cycle, "total_max_amount")
                            # target_amount = round(total_max_amount * ratio, 3)
                            # rest_amount = manager.get(execution_cycle, "rest_amount")
                            # amount = rest_amount if rest_amount < target_amount else target_amount
                            # operation = "close" if rest_amount < target_amount else "reduce"
                            #
                            # client_order_id, timestamp_ms = genius_trader.sell_order(target_stock, amount=amount, price=target_market_price)
                            #
                            # # 添加一条新记录
                            # manager.add_trade_record(
                            #     create_time=datetime.fromtimestamp(timestamp_ms / 1000.0),
                            #     execution_cycle=manager.generate_execution_cycle(strategy_name),
                            #     target_stock=target_stock,
                            #     operation=operation,
                            #     client_order_id=client_order_id,
                            #     price=target_market_price,
                            #     amount=amount,
                            #     value=round(target_market_price * amount, 3),
                            # )

                        long_position = manager.get(execution_cycle, "long_position")
                        print(444)
                        if long_position == 1 + hold_info.get("max_long_position"):
                            sell_times = manager.get(execution_cycle, "sell_times")
                            last_hold_price = manager.get(execution_cycle, "last_hold_price")
                            target_market_price = round(last_hold_price + 0.1 * ATR, 10)
                            if sellLmt < target_market_price and sell_times == hold_info.get("max_sell_times"):
                                # 满仓状态下
                                msg = "减仓(+1.5N线, 追加止盈)"
                                show_time(msg, target_market_price, buyLmt, sellLmt)

                                ratio = 0.3
                                actual_sell(manager, execution_cycle, ratio, genius_trader, target_stock, target_market_price)

                                # total_max_amount = manager.get(execution_cycle, "total_max_amount")
                                # target_amount = round(total_max_amount * ratio, 3)
                                # rest_amount = manager.get(execution_cycle, "rest_amount")
                                # amount = rest_amount if rest_amount < target_amount else target_amount
                                # operation = "close" if rest_amount < target_amount else "reduce"
                                # client_order_id, timestamp_ms = genius_trader.sell_order(target_stock, amount=amount, price=target_market_price)
                                #
                                # # 添加一条新记录
                                # manager.add_trade_record(
                                #     create_time=datetime.fromtimestamp(timestamp_ms / 1000.0),
                                #     execution_cycle=manager.generate_execution_cycle(strategy_name),
                                #     target_stock=target_stock,
                                #     operation=operation,
                                #     client_order_id=client_order_id,
                                #     price=target_market_price,
                                #     amount=amount,
                                #     value=round(target_market_price * amount, 3),
                                # )

                        long_position = manager.get(execution_cycle, "long_position")
                        print(555)
                        if long_position > 0 and flag == 0:
                            # 除数不为零
                            rest_value = manager.get(execution_cycle, "rest_value")  # 累计数量
                            rest_amount = manager.get(execution_cycle, "rest_amount")  # 累计数量
                            hold_average_price = rest_value / rest_amount

                            target_market_price = round(hold_average_price + 0.5 * ATR, 10)
                            if sellLmt < target_market_price:
                                flag = 1
                                msg = "平仓(+0N线, 动态追踪止损)"  # 保本
                                show_time(msg, target_market_price, buyLmt, sellLmt)

                                ratio = 1
                                actual_sell(manager, execution_cycle, ratio, genius_trader, target_stock, target_market_price)

                                # client_order_id, timestamp_ms = genius_trader.sell_order(target_stock, amount=rest_amount, price=target_market_price)
                                #
                                # # 添加一条新记录
                                # manager.add_trade_record(
                                #     create_time=datetime.fromtimestamp(timestamp_ms / 1000.0),
                                #     execution_cycle=manager.generate_execution_cycle(strategy_name),
                                #     target_stock=target_stock,
                                #     operation="close",
                                #     client_order_id=client_order_id,
                                #     price=target_market_price,
                                #     amount=rest_amount,
                                #     value=round(target_market_price * amount, 3),
                                # )

                        long_position = manager.get(execution_cycle, "long_position")
                        if long_position > 0 and flag == 0:
                            stop_loss_price = round(open_price - 0.5 * ATR, 10)
                            # 根据条件选择target_market_price
                            if sellLmt < max(stop_loss_price, down_Dochian_price) and long_position > 0 and flag == 0:
                                target_market_price = max(stop_loss_price, down_Dochian_price)
                                msg = "平仓max(-0.5N线/唐奇安)"
                            elif sellLmt < min(stop_loss_price, down_Dochian_price) and long_position > 0 and flag == 0:
                                target_market_price = min(stop_loss_price, down_Dochian_price)
                                msg = "平仓min(-0.5N线/唐奇安)"
                            else:
                                target_market_price = None

                            if target_market_price is not None:
                                flag = 1
                                show_time(msg, target_market_price, buyLmt, sellLmt)
                                LOGGING.info(f"stop_loss: {stop_loss_price}  down:{down_Dochian_price}")

                                ratio = 1
                                actual_sell(manager, execution_cycle, ratio, genius_trader, target_stock, target_market_price)

                                # rest_amount = manager.get(execution_cycle, "rest_amount")
                                #
                                # client_order_id, timestamp_ms = genius_trader.sell_order(target_stock, amount=rest_amount, price=target_market_price)
                                #
                                # # 添加一条新记录
                                # manager.add_trade_record(
                                #     create_time=datetime.fromtimestamp(timestamp_ms / 1000.0),
                                #     execution_cycle=manager.generate_execution_cycle(strategy_name),
                                #     target_stock=target_stock,
                                #     operation="close",
                                #     client_order_id=client_order_id,
                                #     price=target_market_price,
                                #     amount=rest_amount,
                                #     value=round(target_market_price * rest_amount, 3),
                                # )




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
            # LOGGING.info(f'连接断开，正在重连……其他 {e}')
            LOGGING.info(f'连接断开，不重新连接，请检查……其他 {e}')
            break


if __name__ == '__main__':
    strategy_name = 'TURTLE'


    target_stock = "LUNC-USDT"
    target_stock = "BTC-USDT"
    # target_stock = "FLOKI-USDT"
    target_stock = "OMI-USDT"
    # target_stock = "DOGE-USDT"
    # target_stock = "PEPE-USDT"

    # 订阅账户频道的消息
    subscribe_msg = {
        "op": "subscribe",
        "args": [
            {
                "channel": "price-limit",
                "instId": target_stock
            }
        ]
    }


    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
