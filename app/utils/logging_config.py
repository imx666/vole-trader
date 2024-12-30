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
        "quantVole-DOGE": logging_config("quantVole-DOGE"),
        "quantVole-ETH": logging_config("quantVole-ETH"),
        "quantVole-BTC": logging_config("quantVole-BTC"),
        "quantVole-FLOKI": logging_config("quantVole-FLOKI"),
        "quantVole-XRP": logging_config("quantVole-XRP"),
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
        "quantVole-DOGE": {
            "handlers": ["quantVole-DOGE"],
            "level": "DEBUG",
            "propagate": False,
        },
        "quantVole-ETH": {
            "handlers": ["quantVole-ETH"],
            "level": "DEBUG",
            "propagate": False,
        },
        "quantVole-BTC": {
            "handlers": ["quantVole-BTC"],
            "level": "DEBUG",
            "propagate": False,
        },
        "quantVole-FLOKI": {
            "handlers": ["quantVole-FLOKI"],
            "level": "DEBUG",
            "propagate": False,
        },
        "quantVole-XRP": {
            "handlers": ["quantVole-XRP"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
