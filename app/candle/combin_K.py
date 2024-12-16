from datetime import datetime, timedelta


def merge_klines_to_4h_by_time(klines):
    # 确保klines按时间戳升序排列
    klines.sort(key=lambda x: int(x[0]))

    # 初始化变量
    merged_klines = []
    temp_kline = None
    count = 0

    # 将时间戳转换为datetime对象的辅助函数
    def ts_to_datetime(ts_ms):
        return datetime.fromtimestamp(int(ts_ms) / 1000)

    # 获取下一个时间节点的辅助函数
    def get_next_timestamp(dt):
        # 找到最近的整点
        dt = dt.replace(minute=0, second=0, microsecond=0)
        # 找到下一个4小时整点
        if dt.hour % 4 != 0:
            dt += timedelta(hours=4 - (dt.hour % 4))
        return dt

    # 获取第一个时间节点
    start_dt = get_next_timestamp(ts_to_datetime(klines[0][0]))

    for kline in klines:
        ts, o, h, l, c = map(float, kline)  # 转换为浮点数
        kline_dt = ts_to_datetime(ts)

        # 检查当前K线是否属于当前的4小时周期
        while kline_dt >= start_dt + timedelta(hours=4):
            # 如果当前K线已经超过了当前4小时周期，则保存当前周期并开始新周期
            if temp_kline is not None:
                merged_klines.append([
                    str(int(temp_kline['ts'] * 1000)),  # 时间戳转回字符串
                    f"{temp_kline['o']}",  # 开盘价
                    f"{temp_kline['h']}",  # 最高价
                    f"{temp_kline['l']}",  # 最低价
                    f"{temp_kline['c']}"  # 收盘价
                ])
            # 更新到下一个时间节点
            start_dt += timedelta(hours=4)
            # 重置临时K线
            temp_kline = None

        if temp_kline is None:
            # 初始化临时K线
            temp_kline = {
                'ts': start_dt.timestamp(),
                'o': o,
                'h': h,
                'l': l,
                'c': c
            }

        else:
            # 更新临时K线的高低价
            temp_kline['h'] = max(temp_kline['h'], h)
            temp_kline['l'] = min(temp_kline['l'], l)
            temp_kline['c'] = c  # 更新收盘价为当前K线的收盘价

    # 添加最后一个未完成的周期（如果有）
    if temp_kline is not None:
        merged_klines.append([
            str(int(temp_kline['ts'] * 1000)),
            f"{temp_kline['o']}",
            f"{temp_kline['h']}",
            f"{temp_kline['l']}",
            f"{temp_kline['c']}"
        ])

    # 返回按时间戳降序排列的合并后的K线数据
    return sorted(merged_klines, key=lambda x: int(x[0]), reverse=True)


if __name__ == '__main__':

    klines = [['1734098400000', '100291.2', '101030.5', '100221.6', '101030.5'],
              ['1734094800000', '100300', '100530.3', '99950', '100291.2'],
              ['1734091200000', '100356.1', '100477.3', '100148.3', '100299.9'],
              ['1734087600000', '100459.5', '100790', '100314', '100356.1'],
              ['1734084000000', '100111.9', '100570.3', '99915', '100459.6'],
              ['1734080400000', '100274.2', '100338.9', '99900', '100112'],
              ['1734076800000', '100140.1', '100376.5', '99893.6', '100274.2'],
              ['1734073200000', '99698.4', '100239.2', '99501', '100140.1'],
              ['1734069600000', '99887.4', '100100', '99697.3', '99698.4'],
              ['1734066000000', '100013.3', '100174.7', '99850', '99887.3'],
              ['1734062400000', '99738.4', '100061.6', '99662.2', '100013.3'],
              ['1734058800000', '99482.4', '99802.6', '99482.4', '99738.3'],
              ['1734055200000', '99332.5', '99692.8', '99202.2', '99482.4'],
              ['1734051600000', '100077.4', '100155.8', '99200', '99332.4'],
              ['1734048000000', '100001.2', '100348', '99926.6', '100077.4'],
              ['1734044400000', '100438.2', '100479.9', '99879.6', '100001.1'],
              ['1734040800000', '99744.6', '100482.9', '99506', '100438.2'],
              ['1734037200000', '100009.4', '100104.3', '99690', '99743.7'],
              ['1734033600000', '99477.4', '100401.2', '99457', '100012.1'],
              ['1734030000000', '100849.7', '101056', '99307.1', '99477.4'],
              ['1734026400000', '101607.9', '101669.7', '100815.6', '100849.8'],
              ['1734022800000', '101463.6', '101714.2', '101205.4', '101607.7'],
              ['1734019200000', '101795.5', '102538.9', '101459.2', '101463.5'],
              ['1734015600000', '101698.7', '101862.9', '100707.6', '101795.4'],
              ['1734012000000', '100912', '101711.5', '100610.8', '101698'],
              ['1734008400000', '100830.2', '101554', '100523.4', '100911.9'],
              ['1734004800000', '100364.9', '100940.7', '100356.2', '100830'],
              ['1734001200000', '100585.9', '100640', '100177.1', '100364.1'],
              ['1733997600000', '100803.3', '100803.3', '100467.4', '100585.8'],
              ['1733994000000', '100981.4', '101118.1', '100790', '100803.2'],
              ['1733990400000', '100491.2', '101048.3', '100460.9', '100981.4'],
              ['1733986800000', '100584', '100819.2', '100450', '100491.2'],
              ['1733983200000', '100624.5', '100712', '100404', '100583.9'],
              ['1733979600000', '100691.8', '101115.8', '100618.2', '100624.4'],
              ['1733976000000', '101035.5', '101193.9', '100561', '100690.7'],
              ['1733972400000', '101824.3', '101824.7', '100800', '101035.4'],
              ['1733968800000', '100498.8', '101824.3', '100498.8', '101824.3'],
              ['1733965200000', '100758.8', '100863.8', '100337', '100498.7'],
              ['1733961600000', '101117.4', '101192', '100552.1', '100758.7'],
              ['1733958000000', '101200.9', '101486.4', '101056.4', '101117.4'],
              ['1733954400000', '101512', '101884', '101152', '101197.4'],
              ['1733950800000', '101266', '101524.9', '100863.8', '101511.8'],
              ['1733947200000', '101125.5', '101672', '101020.1', '101265.9'],
              ['1733943600000', '100387.8', '101152.9', '100387.7', '101125.4'],
              ['1733940000000', '99767.9', '100777', '99602.9', '100387.8'],
              ['1733936400000', '100574.9', '100981.3', '99650', '99768'],
              ['1733932800000', '100374.2', '101075.9', '100280', '100574.9'],
              ['1733929200000', '99531.4', '100790', '99410', '100374.1'],
              ['1733925600000', '98733.4', '99548', '98360', '99535.4'],
              ['1733922000000', '98233.9', '98851.2', '98063.7', '98733.4'],
              ['1733918400000', '98294.1', '98499.9', '98159', '98233.8'],
              ['1733914800000', '98209', '98454.5', '98136.4', '98294.1'],
              ['1733911200000', '97998.3', '98283.3', '97853', '98208.9'],
              ['1733907600000', '98099.8', '98171.5', '97750', '97998.4'],
              ['1733904000000', '97331.8', '98463.6', '97304.1', '98099.7'],
              ['1733900400000', '97683', '97779.2', '97250', '97331.9'],
              ['1733896800000', '97497.4', '97759.8', '97384.9', '97680.1'],
              ['1733893200000', '97531.9', '97686.4', '97300', '97495.4'],
              ['1733889600000', '97392.1', '97594.1', '97172.4', '97529'],
              ['1733886000000', '97205.9', '97631.7', '97121.3', '97389.5'],
              ['1733882400000', '95755.3', '97437.7', '95672', '97212.5'],
              ['1733878800000', '96409.9', '96638.2', '95666.6', '95755.3'],
              ['1733875200000', '96593.2', '96839.7', '95803.6', '96410'],
              ['1733871600000', '96839.6', '97126.8', '96412', '96593.2'],
              ['1733868000000', '96855.6', '97094.7', '96583.3', '96839.5'],
              ['1733864400000', '96428.1', '97196.3', '96383.4', '96855.5'],
              ['1733860800000', '95848.5', '96699.9', '95605.9', '96428.1'],
              ['1733857200000', '95133.3', '96165.8', '94973.5', '95846.7'],
              ['1733853600000', '94493.7', '95522.2', '94244.3', '95128.3'],
              ['1733850000000', '96308.1', '96388.2', '94388.3', '94482'],
              ['1733846400000', '95656', '96498.7', '94530', '96316'],
              ['1733842800000', '97801.1', '98111', '95626.3', '95655.9'],
              ['1733839200000', '97715.5', '98300', '97133.3', '97807.4'],
              ['1733835600000', '97153.3', '97915.5', '97117.3', '97715.5'],
              ['1733832000000', '97720.6', '97839.7', '96860.1', '97152.1'],
              ['1733828400000', '97683.2', '97921.1', '97428', '97720.6'],
              ['1733824800000', '97489', '97860', '97489', '97683.3'],
              ['1733821200000', '97374.6', '97676.5', '97220.1', '97489'],
              ['1733817600000', '97197.3', '97516.9', '96943', '97374.7'],
              ['1733814000000', '97455.7', '97490', '96896.8', '97197.3'],
              ['1733810400000', '96935.9', '97499.9', '96803.3', '97455.7'],
              ['1733806800000', '97040', '97050', '96508.8', '96935.9'],
              ['1733803200000', '96925.7', '97120.6', '95890', '97039.9'],
              ['1733799600000', '96662.8', '96988.1', '95557.4', '96923'],
              ['1733796000000', '97936.9', '97947.5', '96612.5', '96662.9'],
              ['1733792400000', '97867.8', '98056', '97472', '97937.5'],
              ['1733788800000', '97275.7', '98138.3', '96987.2', '97867.8'],
              ['1733785200000', '96981.4', '97528', '96701.7', '97267.2'],
              ['1733781600000', '96893.9', '97391.8', '94819', '96981.3'],
              ['1733778000000', '96244.2', '97552', '94000', '96893.9'],
              ['1733774400000', '97074.4', '97333.3', '96111.2', '96245.4'],
              ['1733770800000', '97780.1', '97780.1', '97001', '97071.9'],
              ['1733767200000', '97361', '98259.9', '97354.4', '97780.1'],
              ['1733763600000', '97828.2', '98234.6', '97338', '97356.2'],
              ['1733760000000', '97807.9', '98391.8', '97461.6', '97828.1'],
              ['1733756400000', '100149.7', '100424.4', '97512.2', '97805.4'],
              ['1733752800000', '98993.6', '100396.8', '98852.3', '100145.9'],
              ['1733749200000', '98595', '99230.3', '98235.7', '98993.5'],
              ['1733745600000', '98075.2', '98623.7', '97940', '98595'],
              ['1733742000000', '98715.4', '98715.5', '98029.8', '98075.8']]



    # 合并1H K线数据为4H K线数据
    four_hour_klines = merge_klines_to_4h_by_time(klines)

    # 打印结果
    for kline in four_hour_klines[:20]:
        print(kline)