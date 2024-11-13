import logging
import os.path

from loguru import logger


# 1.🎖️先声明一个类继承logging.Handler(制作一件品如的衣服)
class InterceptTimedRotatingFileHandler(logging.Handler):
    """
    自定义反射时间回滚日志记录器
    缺少命名空间
    """

    def __init__(self, filename, when='d', interval=1, backupCount=15, encoding="utf-8", delay=False, utc=False,
                 atTime=None, logging_levels="all"):
        super(InterceptTimedRotatingFileHandler, self).__init__()
        filename = os.path.abspath(filename)
        when = when.lower()
        # 2.🎖️需要本地用不同的文件名做为不同日志的筛选器
        self.logger_ = logger.bind(sime=filename)
        self.filename = filename
        key_map = {
            'h': 'hour',
            'w': 'week',
            's': 'second',
            'm': 'minute',
            'd': 'day',
        }
        # 根据输入文件格式及时间回滚设立文件名称
        rotation = "%d %s" % (interval, key_map[when])
        retention = "%d %ss" % (backupCount, key_map[when])
        time_format = "{time:%Y-%m-%d_%H-%M-%S}"
        if when == "s":
            time_format = "{time:%Y-%m-%d_%H-%M-%S}"
        elif when == "m":
            time_format = "{time:%Y-%m-%d_%H-%M}"
        elif when == "h":
            time_format = "{time:%Y-%m-%d_%H}"
        elif when == "d":
            time_format = "{time:%Y-%m-%d}"
        elif when == "w":
            time_format = "{time:%Y-%m-%d}"
        filename_fmt = filename.replace(".log", "_%s.log" % time_format)
        file_key = {_._name: han_id for han_id, _ in self.logger_._core.handlers.items()}
        filename_fmt_key = "'{}'".format(filename_fmt)
        if filename_fmt_key in file_key:
            return
        self.logger_.add(
            filename_fmt,
            retention=retention,
            encoding=encoding,
            level="DEBUG",
            rotation=rotation,
            delay=delay,
            enqueue=True,
            filter=lambda x: x['extra'].get('sime') == filename
        )

    def emit(self, record):
        try:
            level = self.logger_.level(record.levelname).name
        except ValueError:
            level = record.levelno

        try:
            frame, depth = logging.currentframe(), 2
            # 6.🎖️把当前帧的栈深度回到发生异常的堆栈深度，不然就是当前帧发生异常而无法回溯
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1
            self.logger_.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())
        except Exception as e:
            self.logger_.error(e)
