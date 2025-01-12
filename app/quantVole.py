import sys
import time
from sqlite3 import OperationalError

import redis
from utils.url_center import redis_url

from MsgSender.feishu_msg import send_feishu_info
from module.trade_records import TradeRecordManager
from module.trade_assistant import hold_info
from module.trade_assistant import TradeAssistant
from module.trade_assistant import timed_task, get_real_time_info
from module.trade_assistant import compute_amount, compute_sb_price, trade_auth, slip, check_state

# 第一个参数是脚本名称，后续的是传入的参数
if len(sys.argv) > 1:
    target_stock = sys.argv[1]  # 这里会得到 '123'
    print(f"The argument target_stock is: {target_stock}")
else:
    print("Error: No arguments were passed. Please provide an target_stock and try again!")
    sys.exit(1)  # 使用非零状态码表示异常退出

sort_name = target_stock.split('-')[0]

import logging.config
from utils.logging_config import Logging_dict

logging.config.dictConfig(Logging_dict)
LOGGING = logging.getLogger(f"quantVole-{sort_name}")

# 相关参数
redis_okx = redis.Redis.from_url(redis_url)
last_read_time = redis_okx.hget(f"common_index:{target_stock}", 'last_read_time')
DayStamp = last_read_time.decode() if last_read_time is not None else None
hold_info.DayStamp = DayStamp

# 持仓信息
hold_info.LOGGING = LOGGING
hold_info.new_stock(target_stock)

# 拉取执行编号
execution_cycle = hold_info.get("execution_cycle")

# sbb()
# time.sleep(123456)


# 交易助手
agent = TradeAssistant('TURTLE', target_stock, trade_type="actual", LOGGING=LOGGING)


def notice_change(long_position, sell_times):
    if long_position != hold_info.get("long_position") or sell_times != hold_info.get("sell_times"):
        global execution_cycle
        LOGGING.info("持仓发生变化,立即拉取redis")
        execution_cycle = hold_info.newest("execution_cycle")
        compute_sb_price(target_stock)


def build_house(target_market_price, order_type="limit"):
    # 生成新编号
    global execution_cycle
    sqlManager = TradeRecordManager(target_stock, "TURTLE")
    execution_cycle = sqlManager.generate_execution_cycle()

    # 买入
    amount = compute_amount("build", target_market_price)
    agent.buy("build", execution_cycle, target_market_price, amount, remark="建仓", order_type=order_type)
    new_info = {
        "pending_order": 1,
        "execution_cycle": execution_cycle,  # 同步新编号
        "tradeFlag": "build"
    }
    hold_info.pull_dict(new_info)


def add_house(target_market_price, order_type="limit"):
    amount = compute_amount("add", target_market_price)
    agent.buy("add", execution_cycle, target_market_price, amount, remark="加仓", order_type=order_type)
    hold_info.pull("pending_order", 1)
    new_info = {
        "pending_order": 1,
        "tradeFlag": "buy-only"
    }
    hold_info.pull_dict(new_info)


def decrease_house(target_market_price, sell_times, order_type="limit"):
    ratio = 0.3 if sell_times <= 1 else 0.2
    operation = "reduce"
    if sell_times == hold_info.get("<max_sell_times>") - 1:  # 不能是完全的多头满的状态来
        ratio = 1
        operation = "close"

    if order_type == "market":
        msg = f"减仓<市价>(+{0.5 * sell_times + 2}N线, 分批止盈)"
    else:
        msg = f"减仓(+{0.5 * sell_times + 2}N线, 分批止盈)"

    agent.sell(operation, execution_cycle, target_market_price, ratio, remark=msg, order_type=order_type)
    new_info = {
        "pending_order": 1,
        "tradeFlag": "sell-only"  # 不能给no-auth，任何时候都得保证最后的平仓可以顺利进行
    }
    hold_info.pull_dict(new_info)


def close_house(close_price, order_type="limit"):
    global execution_cycle

    # 取消所有挂单
    LOGGING.info("取消所有挂单并平仓")
    check_state(target_stock, withdraw_order=True, LOGGING=LOGGING)

    price_dict = hold_info.price_dict
    msg = price_dict["close_type"]
    ratio = 1
    agent.sell("close", execution_cycle, close_price, ratio, remark=msg, order_type=order_type)
    new_info = {
        "pending_order": 1,
        "tradeFlag": "no-auth"
    }
    hold_info.pull_dict(new_info)

    LOGGING.info("休眠10s并等待成交")
    time.sleep(10)

    # 检查平仓是否顺利进行
    check_state(target_stock, withdraw_order=False, LOGGING=LOGGING)
    execution_cycle = hold_info.newest("execution_cycle")
    LOGGING.info(f"平仓已完成, 新execution_cycle: {execution_cycle}")


def circle():
    global execution_cycle

    # 计算目标价
    compute_sb_price(target_stock)

    try:
        while True:
            # 更新策略参数
            timed_task()

            # 挂单数大于零直接跳过
            pending_order = hold_info.newest("pending_order")
            long_position = hold_info.newest("long_position")
            if pending_order > 0 and long_position == 0:  # 空仓有挂单可以直接跳过
                time.sleep(1)
                continue

            # 获取最新报价
            data_dict = get_real_time_info(target_stock)
            if data_dict is None:
                time.sleep(0.05)
                continue

            now_price = data_dict["now_price"]
            agent.now_price = now_price
            sell_times = hold_info.newest("sell_times")

            # 持仓改变，更新策略参数
            notice_change(long_position, sell_times)

            # 获取目标价
            price_dict = hold_info.price_dict

            # 空仓时
            if long_position == 0:
                target_market_price = price_dict['build_price(ideal)']
                if target_market_price - slip(now_price) < now_price:
                    if not trade_auth("buy"):
                        continue

                    # 建仓
                    build_house(target_market_price)
                    continue

            # 未满仓,加仓
            if 0 < long_position < hold_info.get("<max_long_position>"):
                target_market_price = price_dict['add_price_list(ideal)'][long_position - 1]
                if target_market_price - slip(now_price) < now_price:
                    if not trade_auth("buy"):
                        continue

                    # 买入
                    add_house(target_market_price)
                    continue

            # 卖出 ============= SELL =========SELL===========SELL===================== SELL

            # 有持仓的情况下，判断完止损后再跳
            if long_position > 0:
                # 止损
                close_price = price_dict["close_price(ideal)"]
                if now_price < close_price:
                    if not trade_auth("close"):
                        continue

                    # 市价全平
                    close_house(close_price, order_type="market")
                    continue

            # 满仓情况,逐步卖出
            if long_position == hold_info.get("<max_long_position>") and sell_times < hold_info.get(
                    "<max_sell_times>"):
                target_market_price = price_dict['reduce_price_list(ideal)'][sell_times]
                if now_price < target_market_price:
                    if not trade_auth("sell"):
                        continue

                    # 限价卖出
                    decrease_house(target_market_price, sell_times)
                    continue

                if now_price > target_market_price:
                    if not trade_auth("sell"):
                        continue

                    # 市价卖出
                    decrease_house(target_market_price, sell_times, order_type="market")
                    continue

    except KeyboardInterrupt:
        LOGGING.info(f"{target_stock} 手动终止成功")

    except OperationalError as e:
        # (pymysql.err.OperationalError)(2006, "MySQL server has gone away (BrokenPipeError(32, 'Broken pipe'))")
        # (Background on this error at: https://sqlalche.me/e/20/e3q8)
        if e.args[0] == 2006:
            LOGGING.error("MySQL 服务器连接断开，尝试重新连接")
            # 在这里可以选择重新连接数据库或者其他处理逻辑
            # 例如：重新创建连接对象或退出程序

        else:
            LOGGING.error(f"捕获到其他数据库错误: {e}")
            # 处理其他 OperationalError 错误

    except Exception as e:
        e = str(e)
        LOGGING.error(e)
        res = send_feishu_info(f"Error: {execution_cycle}", e, supreme_auth=True, jerry_mouse=True)
        LOGGING.info(res)


if __name__ == '__main__':
    # 开始执行
    circle()
