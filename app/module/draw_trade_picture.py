import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

import pandas as pd
import mplfinance as mpf
import json
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# 绘制蜡烛图的函数
def plot_candlestick(ax, df):
    # 定义价格数据
    up = df[df['close'] >= df['open']]
    down = df[df['close'] < df['open']]

    # 绘制上涨的K线（收盘价高于开盘价，绿色）
    ax.bar(up.index, up['close'] - up['open'], bottom=up['open'], color='green', width=0.8)
    ax.bar(up.index, up['high'] - up['close'], bottom=up['close'], color='green', width=0.2)
    ax.bar(up.index, up['low'] - up['open'], bottom=up['open'], color='green', width=0.2)

    # 绘制下跌的K线（开盘价高于收盘价，红色）
    ax.bar(down.index, down['close'] - down['open'], bottom=down['open'], color='red', width=0.8)
    ax.bar(down.index, down['high'] - down['open'], bottom=down['open'], color='red', width=0.2)
    ax.bar(down.index, down['low'] - down['close'], bottom=down['close'], color='red', width=0.2)


def draw_picture(target_stock, buy_days, sell_days, sell_empty_days, start_day=None, end_day=None, UpDochianChannel=None, DownDochianChannel=None, return_rate_list=None):
    import os
    from pathlib import Path
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    total_path = os.path.join(BASE_DIR, f"./data/{target_stock}.json")
    # 读取并处理 K 线数据
    with open(total_path, 'r') as file:
        long_period_candle = json.load(file)

    # long_period_candle = long_period_candle[200:350]
    if end_day is not None:
        long_period_candle = long_period_candle[start_day:end_day]

    df = pd.DataFrame(long_period_candle, columns=['timestamp', 'open', 'high', 'low', 'close'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].astype(float)
    df.set_index('timestamp', inplace=True)

    # 创建图形和轴
    fig, ax1 = plt.subplots(figsize=(10, 6))

    # 绘制蜡烛图
    plot_candlestick(ax1, df)

    # 将卖出数据转换成 DataFrame
    buy_df = pd.DataFrame(buy_days, columns=['timestamp', 'value'])
    buy_df['timestamp'] = pd.to_datetime(buy_df['timestamp'], unit='ms')

    sell_df = pd.DataFrame(sell_days, columns=['timestamp', 'value'])
    sell_df['timestamp'] = pd.to_datetime(sell_df['timestamp'], unit='ms')

    sell_empty_df = pd.DataFrame(sell_empty_days, columns=['timestamp', 'value'])
    sell_empty_df['timestamp'] = pd.to_datetime(sell_empty_df['timestamp'], unit='ms')


    UpDochianChannel_df = pd.DataFrame(UpDochianChannel, columns=['timestamp', 'value'])
    UpDochianChannel_df['timestamp'] = pd.to_datetime(UpDochianChannel_df['timestamp'], unit='ms')
    DownDochianChannel_df = pd.DataFrame(DownDochianChannel, columns=['timestamp', 'value'])
    DownDochianChannel_df['timestamp'] = pd.to_datetime(DownDochianChannel_df['timestamp'], unit='ms')



    # 连线
    plt.plot(
        UpDochianChannel_df['timestamp'],
        UpDochianChannel_df['value'],
        color='green',
        label='Up Line',
        linestyle='-',
        linewidth=1
    )
    plt.plot(
        DownDochianChannel_df['timestamp'],
        DownDochianChannel_df['value'],
        color='red',
        label='Down Line',
        linestyle='-',
        linewidth=1
        )

    # 在指定的位置绘制卖出点
    plt.scatter(buy_df['timestamp'], buy_df['value'], color='blue', label='Buy Points', s=10)
    plt.scatter(sell_df['timestamp'], sell_df['value'], color='yellow', label='Sell Points', s=15)
    plt.scatter(sell_empty_df['timestamp'], sell_empty_df['value'], color='orange', label='Sell empty Points', s=20)

    # 设置日期格式
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax1.xaxis.set_major_locator(mdates.DayLocator(interval=10))  # 设置x轴间隔
    plt.xticks(rotation=45)

    # 设置图表标题和标签
    ax1.set_title(f'{target_stock} K-Line Chart')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Price')

    # 图例和标题
    # ax1.legend(loc='upper left')
    # ax2.legend(loc='upper right')



    # 回报率
    return_rate_df = pd.DataFrame(return_rate_list, columns=['timestamp', 'return_rate'])
    return_rate_df['timestamp'] = pd.to_datetime(return_rate_df['timestamp'], unit='ms')# 创建右侧轴
    ax2 = ax1.twinx()
    ax2.set_ylim(-0.1, 1)
    # 根据return_rate的值选择颜色
    colors = ['green' if rate > 0 else 'red' for rate in return_rate_df['return_rate']]
    # 绘制回报率柱状图（右轴）
    ax2.bar(
        return_rate_df['timestamp'],
        return_rate_df['return_rate'],
        color=colors,
        alpha=0.6,
        label='Return Rate',
        width=1
    )
    ax2.axhline(y=0, color='black', linestyle='--', linewidth=1)
    # ax2.set_ylabel('Return Rate', color='orange')
    # ax2.tick_params(axis='y', labelcolor='orange')




    # 美化图表
    # plt.legend()
    # plt.tight_layout()

    # 显示图表
    plt.show()


if __name__ == '__main__':
    buy_days = [['1714752000000', 0.15109], ['1714752000000', 0.157343], ['1714752000000', 0.163596],
                ['1714752000000', 0.169849], ['1715616000000', 0.15416], ['1715788800000', 0.159168],
                ['1716220800000', 0.161382], ['1716220800000', 0.164993], ['1717516800000', 0.16475],
                ['1719331200000', 0.12783], ['1720886400000', 0.11246], ['1720972800000', 0.114886],
                ['1720972800000', 0.117312], ['1720972800000', 0.119738], ['1723305600000', 0.10799],
                ['1724083200000', 0.10496], ['1724256000000', 0.107122], ['1724342400000', 0.1093],
                ['1724428800000', 0.112532], ['1725897600000', 0.0995], ['1725897600000', 0.102013],
                ['1725897600000', 0.104526], ['1726156800000', 0.106421], ['1726761600000', 0.10642],
                ['1726848000000', 0.108891], ['1727280000000', 0.111414], ['1727280000000', 0.113911]]
    sell_days = [['1715443200000', 0.14208], ['1716220800000', 0.168604], ['1716998400000', 0.16155],
                 ['1717776000000', 0.15469], ['1719936000000', 0.12051], ['1721059200000', 0.12328],
                 ['1721404800000', 0.133196], ['1721577600000', 0.140676], ['1721836800000', 0.12327],
                 ['1723737600000', 0.10006], ['1724428800000', 0.115056], ['1724688000000', 0.10346],
                 ['1726502400000', 0.09913], ['1727280000000', 0.116408], ['1727366400000', 0.124012]]
    sell_empty_days = [['1715443200000', 0.14208], ['1716998400000', 0.16155], ['1717776000000', 0.15469],
                       ['1719936000000', 0.12051], ['1721836800000', 0.12327], ['1723737600000', 0.10006],
                       ['1724688000000', 0.10346], ['1726502400000', 0.09913]]

    target_stock = "LUNC-USDT"
    target_stock = "BTC-USDT"
    # target_stock = "FLOKI-USDT"
    # target_stock = "OMI-USDT"
    target_stock = "DOGE-USDT"
    # target_stock = "PEPE-USDT"

    draw_picture(target_stock, buy_days, sell_days, sell_empty_days)
