import pandas as pd
import mplfinance as mpf
import json
from datetime import datetime



import os
from pathlib import Path
from dotenv import load_dotenv

project_path = Path(__file__).resolve().parent  # 此脚本的运行"绝对"路径
dotenv_path = os.path.join(project_path, '../.env.dev')  # 指定.env.dev文件的路径
load_dotenv(dotenv_path)  # 载入环境变量
BASE_DIR = Path(__file__).resolve().parent.parent

target_stock = "LUNC-USDT"
target_stock = "BTC-USDT"
target_stock = "FLOKI-USDT"
target_stock = "OMI-USDT"
target_stock = "DOGE-USDT"
target_stock = "PEPE-USDT"

total_path = os.path.join(BASE_DIR, f"./data/{target_stock}.json")
with open(total_path, 'r') as file:
    long_period_candle = json.load(file)




# 将数据转换为DataFrame格式
df = pd.DataFrame(long_period_candle, columns=['timestamp', 'open', 'high', 'low', 'close'])

# 将timestamp从毫秒转换为日期格式
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

# 将数据类型转换为float
df['open'] = df['open'].astype(float)
df['high'] = df['high'].astype(float)
df['low'] = df['low'].astype(float)
df['close'] = df['close'].astype(float)

# 设置timestamp为索引
df.set_index('timestamp', inplace=True)

# 反转数据顺序，使日期从小到大
# df = df.iloc[::-1]

# 使用mplfinance绘制K线图
# mpf.plot(df, type='candle', style='charles', title='K线图', ylabel='价格')
mpf.plot(df, type='candle', style='charles', title=f'K-picture-{target_stock}', ylabel='price')
