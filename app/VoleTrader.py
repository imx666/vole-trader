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
LOGGING = logging.getLogger("VoleTrader")

from MsgSender.wx_msg import send_wx_info
from MsgSender.feishu_msg import send_feishu_info
from module.redis_url import redis_url
from module.genius_trading import GeniusTrader
from module.trade_records import TradeRecordManager
from module.trade_assistant import TradeAssistant
from monitor.monitor_account import check_state
from monitor.monitor_account import HoldInfo
from monitor.monitor_account import prepare_login

ATR = 999999
up_Dochian_price = 999999
down_Dochian_price = 0
SellFlag = 0


def show_moment(msg, target_market_price, buyLmt, sellLmt):
    LOGGING.info(msg)
    LOGGING.info(f"target_market_price: {target_market_price}")
    LOGGING.info(f"buyLmt: {buyLmt}, sellLmt: {sellLmt}")


def actual_sell(hold_info, sqlManager, execution_cycle, ratio, geniusTrader, target_market_price):
    total_max_amount = sqlManager.get(execution_cycle, "total_max_amount")
    target_amount = round(total_max_amount * ratio, 3)
    rest_amount = sqlManager.get(execution_cycle, "rest_amount")
    amount = rest_amount if rest_amount < target_amount else target_amount
    operation = "close" if rest_amount < target_amount else "reduce"

    client_order_id, timestamp_ms = geniusTrader.sell_order(amount=amount, price=target_market_price)

    # 添加一条新记录
    sqlManager.add_trade_record(
        create_time=datetime.fromtimestamp(timestamp_ms / 1000.0),
        execution_cycle=execution_cycle,
        operation=operation,
        client_order_id=client_order_id,
        price=target_market_price,
        amount=amount,
        value=round(target_market_price * amount, 3),
    )


def simulate_sell(hold_info, sqlManager, execution_cycle, ratio, geniusTrader, target_market_price):
    total_max_amount = sqlManager.get(execution_cycle, "total_max_amount")
    target_amount = round(total_max_amount * ratio, 3)
    rest_amount = sqlManager.get(execution_cycle, "rest_amount")
    amount = rest_amount if rest_amount < target_amount else target_amount
    operation = "close" if rest_amount < target_amount else "reduce"

    timestamp_seconds = time.time()
    timestamp_ms = int(timestamp_seconds * 1000)  # 转换为毫秒
    sort_name = target_stock.split("-")[0]
    client_order_id = f"{sort_name}{timestamp_ms}"
    # 添加一条新记录
    sqlManager.add_trade_record(
        create_time=datetime.fromtimestamp(timestamp_ms / 1000.0),
        execution_cycle=execution_cycle,
        operation=operation,
        client_order_id=client_order_id,
        price=target_market_price,
        amount=amount,
        value=round(target_market_price * amount, 3),
    )


def actual_buy(operation, hold_info, sqlManager, execution_cycle, geniusTrader, target_market_price):
    amount = round(hold_info.get("risk_rate") * hold_info.get("init_balance") / ATR, 5)
    client_order_id, timestamp_ms = geniusTrader.buy_order(amount=amount, price=target_market_price)

    # 添加一条新记录
    sqlManager.add_trade_record(
        create_time=datetime.fromtimestamp(timestamp_ms / 1000.0),
        execution_cycle=execution_cycle,
        operation=operation,
        client_order_id=client_order_id,
        price=target_market_price,
        amount=amount,
        value=round(amount * target_market_price, 3),
    )


def simulate_buy(operation, hold_info, sqlManager, execution_cycle, geniusTrader, target_market_price):
    amount = round(hold_info.get("risk_rate") * hold_info.get("init_balance") / ATR, 5)

    timestamp_seconds = time.time()
    timestamp_ms = int(timestamp_seconds * 1000)  # 转换为毫秒
    sort_name = target_stock.split("-")[0]
    client_order_id = f"{sort_name}{timestamp_ms}"
    # 添加一条新记录
    sqlManager.add_trade_record(
        create_time=datetime.fromtimestamp(timestamp_ms / 1000.0),
        execution_cycle=execution_cycle,
        operation=operation,
        client_order_id=client_order_id,
        price=target_market_price,
        amount=amount,
        value=round(amount * target_market_price, 3),
    )


def load_reference_index(target_stock):
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


def timed_task(sqlManager, geniusTrader):
    bj_tz = timezone(timedelta(hours=8))
    now_bj = datetime.now().astimezone(bj_tz)
    # today = now_bj.day  # 当前月份的第几天
    hour_of_day = now_bj.hour  # 第几时
    minute = now_bj.minute  # 第几分

    if hour_of_day in [0, 4, 8, 12, 16, 20] and minute == 2:
        global DayStamp, SellFlag
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        if DayStamp is not None and current_time == DayStamp:
            return

        res = send_wx_info("读取最新策略参数", f"{current_time}", supreme_auth=True)
        LOGGING.info(res)

        load_reference_index(target_stock)
        DayStamp = current_time
        redis_okx.hset(f"common_index:{target_stock}", 'last_read_time', current_time)
        LOGGING.info(f"到点了 :{current_time} ")

        # 更新hold_info
        hold_info.newest_all()

        # 取消未成交的挂单
        check_state(sqlManager, geniusTrader, withdraw_order=True)
        SellFlag = 0


async def main():
    while True:
        reconnect_attempts = 0

        # 更新震荡参数
        flag_exit = load_reference_index(target_stock)
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

                        # 更新策略参数
                        timed_task(sqlManager, geniusTrader)

                        # response = await websocket.recv()
                        response = await asyncio.wait_for(websocket.recv(), timeout=25)
                        data_dict = json.loads(response)
                        buyLmt = float(data_dict["data"][0]["buyLmt"])
                        sellLmt = float(data_dict["data"][0]["sellLmt"])
                        # LOGGING.info(f"buyLmt: {buyLmt}, sellLmt: {sellLmt}")

                        # execution_cycle = sqlManager.last_execution_cycle(strategy_name)  # 获取编号
                        # execution_cycle = hold_info.newest("execution_cycle")
                        long_position = hold_info.newest("long_position")
                        # print(111)
                        if long_position == 0:
                            target_market_price = up_Dochian_price
                            if hold_info.newest("build_state") == 0 and target_market_price < buyLmt:
                                SellFlag = 1
                                execution_cycle = sqlManager.generate_execution_cycle(strategy_name)  # 生成新编号
                                show_moment("建仓", target_market_price, buyLmt, sellLmt)

                                amount = round(hold_info.get("risk_rate") * hold_info.get("init_balance") / ATR, 5)
                                agent.actual_buy("build", execution_cycle, target_market_price, amount)
                                # actual_buy("build", hold_info, sqlManager, execution_cycle, geniusTrader,
                                #            target_market_price)
                                # simulate_buy("build", hold_info, sqlManager, execution_cycle, geniusTrader,
                                #              target_market_price)
                                hold_info.pull("build_state", 1)
                                hold_info.pull("execution_cycle", execution_cycle)  # 同步新编号

                        long_position = hold_info.newest("long_position")
                        # print(222)
                        if 0 < long_position <= hold_info.get("max_long_position"):
                            build_price = hold_info.newest("build_price")
                            target_market_price = round(build_price + long_position * 0.5 * ATR, 10)
                            hold_info.pull("target_market_price(add)", target_market_price)
                            if target_market_price < buyLmt:
                                SellFlag = 1
                                show_moment("加仓", target_market_price, buyLmt, sellLmt)
                                amount = round(hold_info.get("risk_rate") * hold_info.get("init_balance") / ATR, 5)
                                agent.actual_buy("add", execution_cycle, target_market_price, amount)
                                # actual_buy("add", hold_info, sqlManager, execution_cycle, geniusTrader,
                                #            target_market_price)
                                # simulate_buy("add", hold_info, sqlManager, execution_cycle, geniusTrader,
                                #              target_market_price)

                        # ============= SELL =========SELL===========SELL========

                        # 卖出
                        long_position = hold_info.newest("long_position")
                        # print(333)
                        if long_position == 1 + hold_info.get("max_long_position"):
                            build_price = hold_info.newest("build_price")
                            sell_times = sqlManager.get(execution_cycle, "sell_times")
                            target_market_price = round(build_price + (0.5 * sell_times + 2) * ATR, 10)
                            hold_info.pull("target_market_price(sell)", target_market_price)
                            if sellLmt < target_market_price and sell_times < hold_info.get("max_sell_times"):
                                msg = f"减仓(+{0.5 * sell_times + 2}N线, 分批止盈)"
                                show_moment(msg, target_market_price, buyLmt, sellLmt)

                                ratio = 0.3 if sell_times <= 1 else 0.2
                                agent.actual_sell(execution_cycle, target_market_price, ratio)
                                # actual_sell(hold_info, sqlManager, execution_cycle, ratio, geniusTrader,
                                #             target_market_price)
                                # simulate_sell(hold_info, sqlManager, execution_cycle, ratio, geniusTrader,
                                #               target_market_price)

                        long_position = hold_info.newest("long_position")
                        # print(444)
                        if long_position == 1 + hold_info.get("max_long_position"):
                            sell_times = sqlManager.get(execution_cycle, "sell_times")
                            last_hold_price = sqlManager.get(execution_cycle, "last_hold_price")
                            target_market_price = round(last_hold_price + 0.1 * ATR, 10)
                            hold_info.pull("target_market_price(sell)", target_market_price)
                            if sellLmt < target_market_price and sell_times == hold_info.get("max_sell_times"):
                                # 满仓状态下
                                msg = "减仓(+1.5N线, 追加止盈)"
                                show_moment(msg, target_market_price, buyLmt, sellLmt)

                                ratio = 0.3
                                agent.actual_sell(execution_cycle, target_market_price, ratio)
                                # actual_sell(hold_info, sqlManager, execution_cycle, ratio, geniusTrader,
                                #             target_market_price)
                                # simulate_sell(hold_info, sqlManager, execution_cycle, ratio, geniusTrader,
                                #               target_market_price)

                        long_position = hold_info.newest("long_position")
                        # print(555)
                        if long_position > 0 and SellFlag == 0:
                            # 除数不为零
                            rest_value = sqlManager.get(execution_cycle, "rest_value")  # 累计数量
                            rest_amount = sqlManager.get(execution_cycle, "rest_amount")  # 累计数量
                            hold_average_price = rest_value / rest_amount

                            target_market_price = round(hold_average_price + 0.5 * ATR, 10)
                            if sellLmt < target_market_price:
                                SellFlag = 1
                                msg = "平仓(+0N线, 动态追踪止损)"  # 保本
                                show_moment(msg, target_market_price, buyLmt, sellLmt)

                                ratio = 1
                                agent.actual_sell(execution_cycle, target_market_price, ratio)
                                # actual_sell(hold_info, sqlManager, execution_cycle, ratio, geniusTrader,
                                #             target_market_price)
                                # simulate_sell(hold_info, sqlManager, execution_cycle, ratio, geniusTrader,
                                #               target_market_price)

                        long_position = hold_info.newest("long_position")
                        if long_position > 0 and SellFlag == 0:
                            stop_loss_price = round(build_price - 0.5 * ATR, 10)
                            # 根据条件选择target_market_price
                            if sellLmt < max(stop_loss_price,
                                             down_Dochian_price) and long_position > 0 and SellFlag == 0:
                                target_market_price = max(stop_loss_price, down_Dochian_price)
                                msg = "平仓max(-0.5N线/唐奇安)"
                            elif sellLmt < min(stop_loss_price,
                                               down_Dochian_price) and long_position > 0 and SellFlag == 0:
                                target_market_price = min(stop_loss_price, down_Dochian_price)
                                msg = "平仓min(-0.5N线/唐奇安)"
                            else:
                                target_market_price = None

                            if target_market_price is not None:
                                SellFlag = 1
                                show_moment(msg, target_market_price, buyLmt, sellLmt)
                                LOGGING.info(f"stop_loss: {stop_loss_price}  down:{down_Dochian_price}")

                                ratio = 1
                                agent.actual_sell(execution_cycle, target_market_price, ratio)
                                # actual_sell(hold_info, sqlManager, execution_cycle, ratio, geniusTrader,
                                #             target_market_price)
                                # simulate_sell(hold_info, sqlManager, execution_cycle, ratio, geniusTrader,
                                #               target_market_price)





                    except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed) as e:
                        try:
                            await websocket.send('ping')
                            res = await websocket.recv()
                            LOGGING.info(f"收到: {res}")
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

    # target_stock = "LUNC-USDT"
    target_stock = "BTC-USDT"
    # target_stock = "FLOKI-USDT"
    # target_stock = "OMI-USDT"
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

    redis_okx = redis.Redis.from_url(redis_url)
    last_read_time = redis_okx.hget(f"common_index:{target_stock}", 'last_read_time')
    DayStamp = last_read_time.decode() if last_read_time is not None else None

    geniusTrader = GeniusTrader(target_stock)

    sqlManager = TradeRecordManager(target_stock, strategy_name)
    execution_cycle = sqlManager.last_execution_cycle(strategy_name)  # 获取编号

    hold_info = HoldInfo(target_stock)
    hold_info.pull("execution_cycle", execution_cycle)

    agent = TradeAssistant(sqlManager, geniusTrader)


    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
