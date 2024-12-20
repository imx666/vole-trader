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
        "VoleTrader": logging_config("VoleTrader"),
        "auto_upload_index": logging_config("auto_upload_index"),
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
        "VoleTrader": {
            "handlers": ["VoleTrader"],
            "level": "DEBUG",
            "propagate": False,
        },
        "auto_upload_index": {
            "handlers": ["auto_upload_index"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
