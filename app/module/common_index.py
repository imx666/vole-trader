import pandas as pd


# PERIOD = 5

def get_DochianChannel(total_candle, PERIOD):
    # 获取唐奇安窗口
    history_max_price = 0
    history_min_price = 9999999999

    # part_candle = total_candle[:20]
    part_candle = total_candle[:PERIOD]

    # print(part_candle)
    # print(total_candle)
    for day_candle in part_candle:
        # print(day_candle)
        float_candle = [float(item) for item in day_candle[1:]]
        # print(float_candle)
        if max(float_candle) > history_max_price:
            history_max_price = max(float_candle)
        if min(float_candle) < history_min_price:
            history_min_price = min(float_candle)

    # print(history_max_price)
    # print(history_min_price)
    return history_max_price, history_min_price


def get_ATR(total_candle, PERIOD):
    part_candle = total_candle[:20]
    columns = ['timestamp', 'open', 'high', 'low', 'close']
    df = pd.DataFrame(part_candle, columns=columns)
    df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].astype(float)

    # 计算 True Range (TR)
    df['previous_close'] = df['close'].shift(1)
    df['tr'] = df[['high', 'low', 'previous_close']].apply(
        lambda row: max(row['high'] - row['low'],
                        abs(row['high'] - row['previous_close']),
                        abs(row['low'] - row['previous_close'])), axis=1)

    # 计算 ATR（20天简单移动平均）
    # n = 20
    # df['atr'] = df['tr'].rolling(window=n).mean()
    df['atr'] = df['tr'].rolling(window=PERIOD).mean()

    # 设置显示所有行
    pd.set_option('display.max_rows', None)
    # 输出 ATR 结果
    # print(df[['timestamp', 'tr', 'atr']])

    # 获取最后一行的最后一列的值
    last_value = df[['timestamp', 'tr', 'atr']].iloc[-1, -1]

    # 输出该值
    last_value = float(last_value)
    last_value = round(last_value, 10)
    # print(last_value)

    return last_value
