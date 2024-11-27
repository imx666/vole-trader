import json
import time
import requests

# 获取环境变量
import os

APP_ENV = os.getenv('APP_ENV')
FEISHU_AUTH_CODE = os.getenv("FEISHU_AUTH_CODE")


def send_feishu_info(title, body, custom=None, supreme_auth=False, jerry_mouse=False):
    if supreme_auth is False:
        if APP_ENV != "prod":
            return "非生产环境,feishu_msg没有发送权限"

    FEISHU_AUTH_CODE = os.getenv("FEISHU_AUTH_CODE_jerry") if jerry_mouse else os.getenv("FEISHU_AUTH_CODE_tom")

    api_url = f"https://open.feishu.cn/open-apis/bot/v2/hook/{FEISHU_AUTH_CODE}"

    headers = {
        'Content-Type': 'application/json; charset=utf-8'
    }

    payload = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh-CN": {
                    "title": title,
                    "content": [
                        [
                            {
                                "tag": "text",
                                "text": body
                            },
                            # {
                            #     "tag": "a",
                            #     "text": "点击查看",
                            #     "href": "https://sspai.com/u/100gle/updates"
                            # },
                        ],
                        # [
                        #     {
                        #         "tag": "text",
                        #         "text": body
                        #     },
                        #     {
                        #         "tag": "a",
                        #         "text": "点击查看",
                        #         "href": "https://sspai.com/u/100gle/updates"
                        #     },
                        # ],
                    ]
                }
            }
        }
    }
    if custom is not None:
        payload = custom

    # 文档：https://open.feishu.cn/community/articles/7271149634339422210

    payload_json = json.dumps(payload)
    try:
        response = requests.post(api_url, headers=headers, data=payload_json)
        return response.text
    except Exception as e:
        # print(e)
        result = f"发送失败,错误信息:{e}"
        return result


if __name__ == "__main__":
    from datetime import datetime

    # # 手动设置环境变量
    # os.environ['FEISHU_AUTH_CODE'] = 'ZdRWqVqgVK8NR3M8pDrn7n'
    # os.environ['SEND_PERMISSION'] = 'True'

    from pathlib import Path
    from dotenv import load_dotenv

    project_path = Path(__file__).resolve().parent  # 此脚本的运行"绝对"路径
    # project_path = os.getcwd()  # 此脚本的运行的"启动"路径
    dotenv_path = os.path.join(project_path, '../../.env.dev')  # 指定.env.dev文件的路径
    load_dotenv(dotenv_path)  # 载入环境变量

    FEISHU_AUTH_CODE = os.getenv('FEISHU_AUTH_CODE_tom')
    APP_ENV = os.getenv('APP_ENV')
    print(APP_ENV)
    print(FEISHU_AUTH_CODE)
    APP_ENV = "prod"
    # APP_ENV = "test"

    # res = send_feishu_info("<1003:emailsender> EVN:test",
    #                    "出错学院：健康学院")
    # current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # res = send_feishu_info("<ali>: gwt_college_circle", f"[{APP_ENV}]: {current_time}", supreme_auth=True)
    res = send_feishu_info("校团委验证异常!!!", "发布时间:异常!!!\n异常时间:2024-09-14", jerry_mouse=True)
    print(res)
