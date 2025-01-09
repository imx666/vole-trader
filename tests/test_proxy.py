import requests

PROXY_URL = 'http://hddoxgop:40ye9ko0kudx@198.23.239.134:6540'
PROXY_URL = 'http://hddoxgop:40ye9ko0kudx@154.36.110.199:6853'
# PROXY_URL = "http://127.0.0.1:7890"

# 代理设置
proxy = {
    'http': PROXY_URL,
    'https': PROXY_URL,
}

# 发送请求以检查 IP
try:
    response = requests.get('https://httpbin.org/ip', proxies=proxy)
    print("代理返回的 IP 信息:", response.json())
except requests.exceptions.RequestException as e:
    print(f"请求失败: {e}")