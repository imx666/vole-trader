import json
import os
import time
import schedule
from pathlib import Path

from MsgSender.wx_msg import send_wx_info
from MsgSender.feishu_msg import send_feishu_info
from monitor.account_monitor import check_state, hold_info
import logging.config
from utils.logging_config import Logging_dict

logging.config.dictConfig(Logging_dict)
LOGGING = logging.getLogger("auto_upload_account")

BASE_DIR = Path(__file__).resolve().parent.parent
total_path = os.path.join(BASE_DIR, f"./target_stocks.json")
with open(total_path, 'r') as file:
    stock_dict = json.load(file)

target_stock_li = stock_dict["target_stock_mass"] + stock_dict["target_stock_main"]

# 订阅账户频道的消息
subscribe_msg = {
    "op": "subscribe",
    "args": [
        {
            "channel": "balance_and_position",
        }
    ]
}


def update_chain():
    for hold_stock in target_stock_li:
        try:
            # 验证是否有持仓
            hold_type = hold_info.check_stock(hold_stock)
            if hold_type:
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
