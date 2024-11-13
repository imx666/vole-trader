import json
import time
import requests

# 获取环境变量
import os
APP_ENV = os.getenv('APP_ENV')
BARK_AUTH_CODE = os.getenv("BARK_AUTH_CODE")


def send_apple_info(title, body, group="info", jump_url=None, icon=None, supreme_auth=False):
    # group_list = ["info", "warning", "error", "github"]
    if supreme_auth is False:
        if APP_ENV != "prod":
            return "非生产环境,apple_msg没有发送权限"

    time.sleep(1)  # 防止发送过快

    api_url = f"https://api.day.app/{BARK_AUTH_CODE}/"  # 张智宇api

    headers = {
        'Content-Type': 'application/json; charset=utf-8'
    }

    payload = {
        "title": title,
        "body": body,
        "badge": 1,
        "category": "myNotificationCategory",
        "sound": "glass.caf",
        "group": group,
        # "icon": "",
        # "url": "",
    }

    if os.getenv("IN_DOCKER") == "true":
        payload["icon"] = "https://iuxwilson.top/images/docker2.png"  # docker用他
    else:
        # payload["icon"] = "https://iuxwilson.top/images/shell3d.png"  # sh用他
        payload["icon"] = "https://iuxwilson.top/images/shell.png"  #sh备选

    if icon:
        payload["icon"] = icon

    if jump_url:
        payload["url"] = jump_url

    payload_json = json.dumps(payload)
    try:
        response = requests.post(api_url, headers=headers, data=payload_json)
        return response.text
    except Exception as e:
        # print(e)
        result = f"发送失败,错误信息:{e}"
        return result


if __name__ == "__main__":
    # # 手动设置环境变量
    # os.environ['BARK_AUTH_CODE'] = 'ZdRWqVqgVK8NR3M8pDrn7n'
    # os.environ['SEND_PERMISSION'] = 'True'

    # 指定.env.dev文件的路径
    from pathlib import Path
    from dotenv import load_dotenv

    project_path = Path(__file__).resolve().parent  # 此脚本的运行"绝对"路径
    # project_path = os.getcwd()  # 此脚本的运行的"启动"路径
    # print(project_path)

    dotenv_path = os.path.join(project_path, '../../.env.dev')

    # 载入环境变量
    load_dotenv(dotenv_path)
    BARK_AUTH_CODE = os.getenv('BARK_AUTH_CODE')
    APP_ENV = os.getenv('APP_ENV')
    print(APP_ENV)
    APP_ENV = "prod"

    send_apple_info("大数据学院，更新条数；2",
                    "关于2024年本科教材出版资助项目启动的通知",
                    jump_url="https://nbw.sztu.edu.cn/info/1018/45647.htm")

    res = send_apple_info("<1003:emailsender> APP_EVN:test",
                          "出错学院：健康学院", icon="https://iuxwilson.top/images/github.png")  # github
    print(res)
