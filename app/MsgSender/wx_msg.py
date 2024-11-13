import json
import time
import requests

# 获取环境变量
import os
APP_ENV = os.getenv('APP_ENV')
WX_AUTH_CODE = os.getenv("WX_AUTH_CODE")


def send_wx_info(title, body, custom=None, supreme_auth=False):
    if supreme_auth is False:
        if APP_ENV != "prod":
            return "非生产环境,wx_msg没有发送权限"

    time.sleep(1)  # 防止发送过快

    api_url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={WX_AUTH_CODE}"

    headers = {
        'Content-Type': 'application/json; charset=utf-8'
    }

    payload = {
        "msgtype": "text",
        "text": {
            "content": f"{title}\n{body}",
            # "mentioned_list": ["wangqing", "@all"],
            # "mentioned_mobile_list": ["13800001111", "@all"]
        }
    }
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": f"""<font color=\"warning\">{title}</font>\n
             >错误:<font color=\"comment\">{body}</font>"""
        }
    }
    if custom is not None:
        payload = custom

    # 文档：https://developer.work.weixin.qq.com/document/path/91770
    # markdown支持以下
    """
    1.标题
    ## 标题二
    ### 标题三
    
    2.加粗
    **bold**
    
    3.链接
    [这是一个链接](http://work.weixin.qq.com/api/doc)
    
    4.引用
    > 引用文字
    
    5.颜色
    <font color="info">绿色</font>
    <font color="comment">灰色</font>
    <font color="warning">橙红色</font>
    
    """


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
    # os.environ['WX_AUTH_CODE'] = 'ZdRWqVqgVK8NR3M8pDrn7n'
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
    WX_AUTH_CODE = os.getenv('WX_AUTH_CODE')
    APP_ENV = os.getenv('APP_ENV')
    print(APP_ENV)
    print(WX_AUTH_CODE)
    APP_ENV = "prod"

    res = send_wx_info("<1003:emailsender> EVN:test",
                          "出错学院：健康学院")

    ddd={
        "msgtype": "markdown",
        "markdown": {
            "content": f"""<font color=\"warning\">{title}</font>\n
         >错误:<font color=\"comment\">{body}</font>"""
        }
    }
    res = send_wx_info("1", "1", custom=ddd, supreme_auth=True)
    print(res)
