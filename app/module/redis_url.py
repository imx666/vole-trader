import redis

import os
from pathlib import Path
from dotenv import load_dotenv

project_path = Path(__file__).resolve().parent  # 此脚本的运行"绝对"路径
dotenv_path = os.path.join(project_path, '../../.env.dev')  # 指定.env.dev文件的路径
load_dotenv(dotenv_path)  # 载入环境变量

# 从环境变量中获取 Redis 配置
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_DB_okx = os.getenv("REDIS_DB_okx")

# REDIS_HOST = '127.0.0.1'
# REDIS_HOST = '172.155.0.4'
# REDIS_PORT = 6379
# REDIS_PASSWORD = 123456  # 如果有密码，可以在这里指定
# REDIS_DB = 8  # 默认数据库编号

# 构建 Redis 连接字符串
redis_url = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_okx}'

# # 连接 Redis
# redis_okx = redis.Redis.from_url(redis_url)
#
# # 测试连接
# try:
#     redis_okx.ping()
#     print("Redis connection successful")
# except redis.exceptions.ConnectionError as e:
#     print(f"Redis connection failed: {e}")