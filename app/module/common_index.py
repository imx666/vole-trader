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


def Amplitude(total_candle, side):
    if side == 'up':
        li = []
        total_li = []
        continue_up = 0
        for today_candle in total_candle:
            open_price = float(today_candle[1])
            close_price = float(today_candle[4])
            rate = close_price / open_price
            total_li.append(rate)
            if rate > 1:
                continue_up += 1
                li.append(rate)
        # print("total_li", total_li)
        if continue_up == 0:
            return False, li

        if continue_up == len(total_candle):
            return True, li

        if continue_up == len(total_candle) - 1:
            for item in li:
                total_li.remove(item)
            single = total_li[-1]
            if single > 0.998:
                # print("single", single)
                return True, total_li

        return False, li

    if side == 'down':
        continue_down = 0
        for today_candle in total_candle:
            open_price = float(today_candle[1])
            close_price = float(today_candle[4])
            rate = close_price / open_price
            if rate < 1:
                continue_down += 1
        if continue_down == len(total_candle):
            return True
        return False


if __name__ == '__main__':
    pre_candle = [
        ["1733968800000", "0.00013275", "0.00013364", "0.00013265", "0.00013334"],
        ["1733969700000", "0.00013338", "0.00013466", "0.00013335", "0.00013462"],
        ["1733970600000", "0.00013463", "0.00013637", "0.00013451", "0.00013607"],
        ["1733971500000", "0.00013611", "0.00013744", "0.00013533", "0.00013733"],
        ["1733972400000", "0.0001373", "0.00013815", "0.0001361", "0.0001371"],
        ["1733973300000", "0.0001378", "0.00013885", "0.00013735", "0.00013877"],
    ]
    auth, li = Amplitude(pre_candle, "up")
    if auth:
        print("建仓")
        print(li)
