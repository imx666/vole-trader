#!/bin/bash


#sh ./op/env.sh   #sh指令会创建一个新的子进程，从而使得父进程无法进入虚拟环境
#"""source的含义在当前 shell 进程中执行指定的脚本文件，而不是启动一个新的子进程。"""
#"""source命令可能无法找到，所以可以使用.这个符号来代替"""
. ./op/env.sh


#导入环境变量
if [ ! -f .env.dev ]; then
  echo ".env.dev 文件不存在，请创建并配置必要的环境变量。"
  exit 1
fi
export $(xargs <.env.dev)
export APP_ENV="prod"


# 启动 supervisord
supervisord -n -c ./op/supervisord.conf

echo "supervisord start success!"




