import json
import time

import requests

timestamp_seconds = time.time()
timestamp_ms = int(timestamp_seconds * 1000)  # 转换为毫秒
url = f"https://www.okx.com/v2/support/info/announce/listProject?&t={timestamp_seconds}"

headers = {
    'accept': 'application/json',
    'accept-language': 'zh-CN,zh;q=0.9',
    'app-type': 'web',
    'cache-control': 'no-cache',
    'devid': 'df155d29-e039-4dcb-8f2c-68012c1c0af9',
    'pragma': 'no-cache',
    'priority': 'u=1, i',
    'referer': 'https://www.okx.com/zh-hans/markets/prices',
    'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'x-cdn': 'https://www.okx.com',
    'x-id-group': '2140766107842160002-c-11',
    'x-locale': 'zh_CN',
    'x-site-info': '==QfxojI5RXa05WZiwiIMFkQPx0Rfh1SPJiOiUGZvNmIsICUKJiOi42bpdWZyJye',
    'x-utc': '8',
    'x-zkdex-env': '0',
    # 'Cookie': 'traceId=2140766107842160002; devId=df155d29-e039-4dcb-8f2c-68012c1c0af9; ok_site_info=; locale=zh_CN; ok-exp-time=1736610784222; ok_prefer_currency=%7B%22currencyId%22%3A0%2C%22isDefault%22%3A1%2C%22isPremium%22%3Afalse%2C%22isoCode%22%3A%22USD%22%2C%22precision%22%3A2%2C%22symbol%22%3A%22%24%22%2C%22usdToThisRate%22%3A1%2C%22usdToThisRatePremium%22%3A1%2C%22displayName%22%3A%22%E7%BE%8E%E5%85%83%22%7D; ok_prefer_udColor=0; ok_prefer_udTimeZone=0; __cf_bm=r.Ym_2qE4Ib2KNNRvoBOzLdQZuy7vCj5WTV9.TjoOJA-1736610784-1.0.1.1-lwZawCTjp.crGx10g5TjchksPIGUwwSEiw1vSKXBWVP7DC3fyfWSOljRkygBs.YvGmAxSvU2g_RfVdE1NqGbQw; okg.currentMedia=lg; _monitor_extras={"deviceId":"2RjxR0vTzRwa2eOAzYjNDt","eventId":4,"sequenceNumber":4}; ok-ses-id=X4mbaL2OZI9p0r1116lWk3HuSDENhgrJIuwTnkotRg5EBbDzJKzHTNnz209cD1kar8Lo9U8Diz1Ra3tTDg74h3mjrjMcI9fL8SzF23KB922u4P17VGSh44i5O6QQOt7e; _ga_G0EKWWQGTZ=GS1.1.1736610787.1.0.1736610787.60.0.0; _ga=GA1.2.515561083.1736610787; _gid=GA1.2.1019635994.1736610787; _gat_UA-35324627-3=1; tmx_session_id=a6m7r5a5l1k_1736610791048; intercom-id-ny9cf50h=286c5cff-a59c-4dc4-8e7b-bdc82f9dec05; intercom-session-ny9cf50h=; intercom-device-id-ny9cf50h=86f8bc31-f9cd-4501-86fa-316cf347f07a; fingerprint_id=df155d29-e039-4dcb-8f2c-68012c1c0af9; _ym_uid=1736610794446980782; _ym_d=1736610794; _ym_isad=2; _ym_visorc=b'
}

response = requests.request("GET", url, headers=headers, data={})
json_data = response.json()
# print(json_data)

# json_data2 = json.dumps(json_data)
# with open('market_monitor222.json', 'w', encoding='utf-8') as f:
#    f.write(json_data2)


data_list = json_data["data"]["list"]

key_translation = {
    "changePercentage": "变化百分比",
    "classification": "分类",
    "classificationId": "分类ID",
    "currencyId": "货币ID",
    "dayHigh": "日最高价",
    "dayLow": "日最低价",
    "flowTotal": "总流通量",
    "fullName": "全名",
    "fullNameSeo": "SEO全名",
    "icon": "图标",
    "last": "最新价格",
    "marketCap": "市值",
    "newFlag": "新标志",
    "open": "开盘价",
    "openUtc0": "UTC0开盘价",
    "openUtc8": "UTC8开盘价",
    "project": "项目",
    "quoteCurrencySymbol": "报价货币符号",
    "symbol": "交易对",
    "volume": "交易量"
}

pass_str_li = [
    "icon", "classification", "classificationId", "currencyId", "openUtc0", "openUtc8", "open", "newFlag", "dayHigh",
    "dayLow", "fullName", "fullNameSeo", "quoteCurrencySymbol", "volume"
]

target_small_market = []
sorted_data = sorted(data_list, key=lambda x: x['marketCap'], reverse=True)
# sorted_data = sorted(data_list, key=lambda x: float(x['changePercentage'].replace('%', '')), reverse=True)

for item in sorted_data:
    marketCap = item['marketCap']
    symbol = item['symbol']
    if marketCap == 0 or symbol == "":
        continue
    if 5*10 ** 8 > marketCap > 2*10 ** 8:
        target_small_market.append(item["project"])
    print(item["project"])
    print(item["symbol"])
    print(item["marketCap"])
    print(item["last"])
    print(item["changePercentage"])
    print()
    # for key, value in item.items():
    #     if key in pass_str_li:
    #         continue
    #     chinese_key = key_translation.get(key, key)  # 如果没有找到对应的中文键，则使用原键
    #     print(f"{chinese_key}: {value}")
    # print()

target_small_market2 = [item+"-USDT" for item in target_small_market]
print(target_small_market2)

json_data = json.dumps(target_small_market)
with open('market_monitor.json', 'w', encoding='utf-8') as f:
    f.write(json_data)