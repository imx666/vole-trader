# 使用 python:3.10-buster 作为基础镜像
FROM python:3.10-buster


# 设置时区
ENV TimeZone=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TimeZone /etc/localtime && echo $TimeZone > /etc/timezone


# 设置工作目录
WORKDIR /code


# 安装所需 Python 包
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple


# 将应用程序代码复制到容器中
COPY ./.env.dev ./.env.dev
COPY ./op ./op
COPY ./app ./app


# 设置环境变量说明在docker中
ENV IN_DOCKER=true


# 启动
CMD ["sh", "./op/run.sh"]

