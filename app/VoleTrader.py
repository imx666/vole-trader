import json
import socket
import redis
from datetime import datetime, timezone, timedelta

import asyncio
import websockets

from MsgSender.wx_msg import send_wx_info
from MsgSender.feishu_msg import send_feishu_info
from module.redis_url import redis_url
from module.genius_trading import GeniusTrader
from module.trade_records import TradeRecordManager
from module.trade_assistant import TradeAssistant
from monitor.monitor_account import check_state
from monitor.monitor_account import HoldInfo
from monitor.monitor_account import prepare_login

import logging.config
from utils.logging_config import Logging_dict

logging.config.dictConfig(Logging_dict)
LOGGING = logging.getLogger("VoleTrader")


price_dict = {}

# target_stock = "LUNC-USDT"
# target_stock = "BTC-USDT"
# target_stock = "ETH-USDT"
target_stock = "FLOKI-USDT"
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

# 持仓信息
hold_info = HoldInfo(target_stock)
execution_cycle = hold_info.get("execution_cycle")

# 交易助手
agent = TradeAssistant('TURTLE', target_stock, trade_type="actual")
# agent = TradeAssistant(sqlManager, geniusTrader, trade_type="actual")
# agent = TradeAssistant(sqlManager, geniusTrader, trade_type="simulate")


# 数据库记录
sqlManager = TradeRecordManager("TURTLE")


def trade_auth(side):
    tradeFlag = hold_info.newest("tradeFlag")
    if tradeFlag == "all-auth":
        LOGGING.info("trade approved")
        return True

    if tradeFlag == "no-auth":
        LOGGING.warning("no access to trade")
        return False

    if tradeFlag == "buy-only" and side == "buy":
        LOGGING.info("trade approved")
        return True

    if tradeFlag == "sell-only" and side == "sell":
        LOGGING.info("trade approved")
        return True

    LOGGING.warning("no access to trade")
    return False


def compute_amount(operation, hold_info, target_market_price):
    amount = round(hold_info.get("risk_rate") * hold_info.get("init_balance") / hold_info.get("ATR"), 5)
    rate = 0.3 if operation == "build" else 0.25
    expect_max_cost = hold_info.get("init_balance") * rate
    expect_min_cost = hold_info.get("init_balance") * 0.15
    now_cost = amount * target_market_price
    if now_cost > expect_max_cost:
        LOGGING.info("超预算(减少数量)")
        amount = expect_max_cost / target_market_price
    if expect_min_cost > now_cost:
        LOGGING.info("未达预算(增加数量)")
        amount = expect_min_cost / target_market_price

    return amount


def compute_target_price(ATR, up_Dochian_price, down_Dochian_price):
    global price_dict

    # 计算目标价格
    build_price = hold_info.newest("build_price")
    stop_loss_price = round(build_price - 0.5 * ATR, 10)

    if stop_loss_price > down_Dochian_price:
        close_price = stop_loss_price
        close_type = "-0.5N线"
    else:
        close_price = down_Dochian_price
        close_type = "唐奇安下线"

    price_dict_2_redis = {
        '平仓价(-0.5N线)': '未建仓' if build_price == 0 else stop_loss_price,
        'ATR': ATR,
    }

    price_dict = {
        'ATR': ATR,
        'close_price(ideal)': close_price,
        'close_type': close_type,
    }

    if build_price == 0:
        price_dict_2_redis['build_price(ideal)'] = up_Dochian_price
        price_dict['build_price(ideal)'] = up_Dochian_price

    if build_price > 0:
        hold_info.remove('build_price(ideal)')
        add_price_list = []
        reduce_price_list = []
        build_price = hold_info.newest("build_price")
        long_position = hold_info.newest("long_position")
        sell_times = hold_info.newest("sell_times")
        for i in range(long_position, hold_info.get("max_long_position")):
            target_market_price = round(build_price + i * 0.5 * ATR, 10)
            # target_market_price = build_price + i * 0.5 * ATR
            add_price_list.append(target_market_price)

        for i in range(sell_times, hold_info.get("max_sell_times")):
            target_market_price = round(build_price + (0.5 * i + 2) * ATR, 10)
            # target_market_price = build_price + (0.5 * i + 2) * ATR
            reduce_price_list.append(target_market_price)

        price_dict_2_redis['close_price(ideal)'] = close_price
        price_dict_2_redis['add_price_list(ideal)'] = str(add_price_list)
        price_dict_2_redis['reduce_price_list(ideal)'] = str(reduce_price_list)
        price_dict['close_price(ideal)'] = close_price
        price_dict['close_type'] = close_type
        price_dict['add_price_list(ideal)'] = add_price_list
        price_dict['reduce_price_list(ideal)'] = reduce_price_list

    hold_info.pull_dict(price_dict_2_redis)

    # return price_dict


def load_index_and_compute_price(target_stock):
    # 获取单个字段的值
    name = redis_okx.hget(f"common_index:{target_stock}", 'update_time')
    if name is None:
        raise Exception(f"load_reference_index: redis: {target_stock}股票参数不存在")

    name = name.decode()
    LOGGING.info("开始更新每日参数")
    LOGGING.info(f"参数更新的最后日期: {name}")

    # 获取整个哈希表的所有字段和值
    all_info = redis_okx.hgetall(f"common_index:{target_stock}")

    # 解码每个键和值
    decoded_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in all_info.items()}
    # LOGGING.info(decoded_data)

    up_Dochian_price = float(decoded_data['history_max_price'])
    down_Dochian_price = float(decoded_data['history_min_price'])
    ATR = float(decoded_data['ATR'])

    LOGGING.info(ATR)
    LOGGING.info(up_Dochian_price)
    LOGGING.info(down_Dochian_price)

    compute_target_price(ATR, up_Dochian_price, down_Dochian_price)


def timed_task():
    bj_tz = timezone(timedelta(hours=8))
    now_bj = datetime.now().astimezone(bj_tz)
    # today = now_bj.day  # 当前月份的第几天
    hour_of_day = now_bj.hour  # 第几时
    minute = now_bj.minute  # 第几分

    if hour_of_day in [0, 4, 8, 12, 16, 20] and minute == 2:
        # if hour_of_day in [0, 4, 8, 12, 16, 20] and minute == 20:
        global DayStamp
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        if DayStamp is not None and current_time == DayStamp:
            return

        res = send_wx_info("读取最新策略参数", f"{current_time}", supreme_auth=True)
        LOGGING.info(res)

        load_index_and_compute_price(target_stock)
        DayStamp = current_time
        redis_okx.hset(f"common_index:{target_stock}", 'last_read_time', current_time)
        LOGGING.info(f"到点了 :{current_time} ")

        # 取消未成交的挂单
        # check_state(target_stock, sqlManager, hold_info, geniusTrader, withdraw_order=True)
        check_state(target_stock)

        # 开放交易权限
        hold_info.pull("tradeFlag", "all-auth")  # 同步新编号


async def main():
    global execution_cycle
    while True:
        reconnect_attempts = 0

        try:
            async with websockets.connect('wss://ws.okx.com:8443/ws/v5/public') as websocket:
                # account_msg = prepare_login()
                # LOGGING.info(f"发送登录消息: {account_msg}")
                # await websocket.send(json.dumps(account_msg))
                # response = await websocket.recv()
                # LOGGING.info(f"登录响应: {response}")
                load_index_and_compute_price(target_stock)

                # 发送订阅请求
                await websocket.send(json.dumps(subscribe_msg))
                subscribe_response = await websocket.recv()
                LOGGING.info(f"订阅响应: {subscribe_response}")
                LOGGING.info(f"持续跟踪价格中...")

                # 持续监听增量数据
                while True:
                    try:

                        # 更新策略参数
                        timed_task()

                        response = await asyncio.wait_for(websocket.recv(), timeout=25)
                        data_dict = json.loads(response)
                        buyLmt = float(data_dict["data"][0]["buyLmt"])
                        sellLmt = float(data_dict["data"][0]["sellLmt"])
                        # LOGGING.info(f"buyLmt: {buyLmt}, sellLmt: {sellLmt}")

                        probable_price = (buyLmt + sellLmt) / 2
                        agent.buyLmt, agent.sellLmt = buyLmt, sellLmt
                        long_position = hold_info.newest("long_position")
                        sell_times = hold_info.newest("sell_times")

                        # 空仓时
                        if long_position == 0:
                            # print(111)
                            # 计算目标价格
                            target_market_price = price_dict['build_price(ideal)']
                            if target_market_price < probable_price and hold_info.newest("build_price") == 0:
                                if not trade_auth("sell"):
                                    continue
                                # 生成新编号
                                execution_cycle = sqlManager.generate_execution_cycle()
                                # 计算目标数量
                                amount = compute_amount("build", hold_info, target_market_price)
                                # 买入
                                agent.buy("build", execution_cycle, target_market_price, amount)

                                new_info = {
                                    "build_price", target_market_price,
                                    "execution_cycle", execution_cycle,  # 同步新编号
                                    "tradeFlag", "buy-only"
                                }
                                hold_info.pull_dict(new_info)
                                continue

                        # 未满仓,加仓
                        if 0 < long_position <= hold_info.get("max_long_position"):
                            # print(222)
                            # 计算目标价格
                            target_market_price = price_dict['add_price_list(ideal)'][0]
                            if target_market_price < probable_price:
                                if not trade_auth("sell"):
                                    continue
                                # 计算目标数量
                                amount = compute_amount("add", hold_info, target_market_price)
                                # 买入
                                agent.buy("add", execution_cycle, target_market_price, amount, remark="加仓")
                                price_dict['add_price_list(ideal)'].pop(0)

                                hold_info.pull("tradeFlag", "buy-only")
                                continue

                        # 卖出 ============= SELL =========SELL===========SELL===================== SELL

                        # 满仓情况,逐步卖出
                        # print(333)
                        if long_position == hold_info.get("max_long_position") and sell_times < hold_info.get(
                                "max_sell_times"):
                            # 计算目标价格
                            target_market_price = price_dict['reduce_price_list(ideal)'][0]
                            if probable_price < target_market_price:
                                if not trade_auth("sell"):
                                    continue
                                msg = f"减仓(+{0.5 * sell_times + 2}N线, 分批止盈)"

                                # 卖出
                                ratio = 0.3 if sell_times <= 1 else 0.2
                                agent.sell(execution_cycle, target_market_price, ratio, remark=msg)
                                price_dict['reduce_price_list(ideal)'].pop(0)
                                continue

                        # 止损
                        if long_position > 0:
                            # print(666)
                            close_price = price_dict["close_price(ideal)"]
                            if probable_price < close_price:
                                if not trade_auth("sell"):
                                    continue
                                msg = price_dict["close_type"]
                                ratio = 1
                                agent.sell(execution_cycle, close_price, ratio, remark=msg)

                                new_info = {
                                    "execution_cycle", execution_cycle,  # 同步新编号
                                    "tradeFlag", "no-auth"
                                }
                                hold_info.pull_dict(new_info)

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
            LOGGING.info(f'连接断开，不重新连接，请检查……其他: {e}')
            break


if __name__ == '__main__':
    # 争对此问题！！！
    # 连接断开，不重新连接，请检查……其他: Timeout reading from socket

    # 开始执行
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
