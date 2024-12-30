def logging_config(filename):
    log_dir = os.path.join(BASE_DIR, "logs")
    # log_path = log_dir + ("/%s.log" % filename)
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
    return dict(
        {
            "class": "utils.log.InterceptTimedRotatingFileHandler",
            "filename": os.path.join(BASE_DIR, f"logs/{filename}/{filename}.log"),
            "when": "D",
            "encoding": "utf-8",
            "formatter": "standard",
            "backupCount": 30,
            "interval": 1,
        },
    )


import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# print(BASE_DIR)

Logging_dict = {
    "version": 1,
    "disable_existing_loggers": True,
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] [%(filename)s:%(lineno)d] [%(module)s:%(funcName)s] '
                      '[%(levelname)s]- %(message)s'},
        'simple': {  # 简单格式
            'format': '%(levelname)s %(message)s'
        },
    },
    "handlers": {
        "app_01": logging_config("app_01"),
        "auto_sync_account": logging_config("auto_sync_account"),
        "auto_upload_index": logging_config("auto_upload_index"),
        "auto_upload_account": logging_config("auto_upload_account"),
        "price_monitor": logging_config("price_monitor"),
        "VoleTrader-DOGE": logging_config("VoleTrader-DOGE"),
        "VoleTrader-ETH": logging_config("VoleTrader-ETH"),
        "VoleTrader-BTC": logging_config("VoleTrader-BTC"),
        "VoleTrader-FLOKI": logging_config("VoleTrader-FLOKI"),
        "VoleTrader-XRP": logging_config("VoleTrader-XRP"),
    },
    "loggers": {
        "app_01": {
            "handlers": ["app_01"],
            "level": "DEBUG",
            "propagate": False,
        },
        "auto_sync_account": {
            "handlers": ["auto_sync_account"],
            "level": "DEBUG",
            "propagate": False,
        },
        "auto_upload_account": {
            "handlers": ["auto_upload_account"],
            "level": "DEBUG",
            "propagate": False,
        },
        "auto_upload_index": {
            "handlers": ["auto_upload_index"],
            "level": "DEBUG",
            "propagate": False,
        },
        "price_monitor": {
            "handlers": ["price_monitor"],
            "level": "DEBUG",
            "propagate": False,
        },
        "VoleTrader-DOGE": {
            "handlers": ["VoleTrader-DOGE"],
            "level": "DEBUG",
            "propagate": False,
        },
        "VoleTrader-ETH": {
            "handlers": ["VoleTrader-ETH"],
            "level": "DEBUG",
            "propagate": False,
        },
        "VoleTrader-BTC": {
            "handlers": ["VoleTrader-BTC"],
            "level": "DEBUG",
            "propagate": False,
        },
        "VoleTrader-FLOKI": {
            "handlers": ["VoleTrader-FLOKI"],
            "level": "DEBUG",
            "propagate": False,
        },
        "VoleTrader-XRP": {
            "handlers": ["VoleTrader-XRP"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
