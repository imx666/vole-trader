import time
import schedule
from datetime import datetime, timezone, timedelta

from MsgSender.wx_msg import send_wx_info
from MsgSender.feishu_msg import send_feishu_info
from monitor.account_monitor import check_state
import logging.config
from utils.logging_config import Logging_dict

logging.config.dictConfig(Logging_dict)
LOGGING = logging.getLogger("auto_upload_account")

# 订阅账户频道的消息
subscribe_msg = {
    "op": "subscribe",
    "args": [
        {
            "channel": "balance_and_position",
        }
    ]
}

target_stock_li = [
    "BTC-USDT",
    "ETH-USDT",
    "DOGE-USDT",
    "FLOKI-USDT",
    "XRP-USDT",
    # "LUNC-USDT",
    # "OMI-USDT",
    # "PEPE-USDT",
]


def update_chain():
    for hold_stock in target_stock_li:
        try:
            check_state(hold_stock, withdraw_order=False, LOGGING=LOGGING)
        except Exception as e:
            LOGGING.error(e)


if __name__ == "__main__":
    update_chain()

    # 每5秒执行一次任务
    schedule.every(60).seconds.do(update_chain)

    LOGGING.info("定时任务启动, 每60秒执行一次任务\n")

    # 执行定时任务的主循环
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        LOGGING.info("定时任务已停止")
