# import redis
import os
from pathlib import Path
from dotenv import load_dotenv

project_path = Path(__file__).resolve().parent  # 此脚本的运行"绝对"路径
dotenv_path = os.path.join(project_path, '../../.env.dev')  # 指定.env.dev文件的路径
load_dotenv(dotenv_path)  # 载入环境变量

# 从环境变量中获取 Redis 配置
REDIS_HOST_fastest = os.getenv("REDIS_HOST_fastest")
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_DB_okx = os.getenv("REDIS_DB_okx")

MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")


# 构建 Redis 连接字符串
redis_url = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB_okx}'
redis_url_fastest = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST_fastest}:{REDIS_PORT}/{REDIS_DB_okx}'

# 构建 mysql 连接字符串
DATABASE_URL = f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/trading_db'


# print(redis_url)
# print(DATABASE_URL)
# # 连接 Redis
# redis_okx = redis.Redis.from_url(redis_url)
#
# # 测试连接
# try:
#     redis_okx.ping()
#     print("Redis connection successful")
# except redis.exceptions.ConnectionError as e:
#     print(f"Redis connection failed: {e}")