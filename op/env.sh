#!/bin/sh
echo "Check if running in Docker ..."

if [ "$IN_DOCKER" = "true" ]; then
    echo "Running inside Docker"
else
    set -e
    echo "Not running inside Docker"
    echo "配置并进入虚拟环境"

    python3 -m venv venv
    ./venv/bin/python3 -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
    source ./venv/bin/activate
#    source /root/rundjango/bin/activate  # 有些服务器不支持以上面的方式进入虚拟环境


fi



CRTDIR=$(pwd)
echo "BASE_DIR=$CRTDIR"
export BASE_DIR=$CRTDIR


logs="./logs"
if [ ! -d "$logs" ]; then
  mkdir -p "$logs"
fi

logs="./logs/supervisord/"
if [ ! -d "$logs" ]; then
  mkdir -p "$logs"
fi



