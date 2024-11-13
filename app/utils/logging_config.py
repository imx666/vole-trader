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
        "app_02": logging_config("app_02"),
        "app_03": logging_config("app_03"),
    },
    "loggers": {
        "app_01": {
            "handlers": ["app_01"],
            "level": "DEBUG",
            "propagate": False,
        },
        "app_02": {
            "handlers": ["app_02"],
            "level": "DEBUG",
            "propagate": False,
        },
        "app_03": {
            "handlers": ["app_03"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
