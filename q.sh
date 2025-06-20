#!/bin/bash
# PDF证书管理系统生产环境启动脚本

# 设置环境变量
export FLASK_CONFIG=production
export PYTHONPATH=/www/pdf:$PYTHONPATH

PID_FILE="logs/gunicorn.pid"

# 创建必要的目录
mkdir -p logs
mkdir -p uploads/temp

# 检查是否已经在运行
if [ -f "$PID_FILE" ] && ps -p $(cat $PID_FILE) > /dev/null 2>&1; then
    echo "PDF证书管理系统已经在运行 (PID: $(cat $PID_FILE))"
    echo "如需停止服务，请运行：./stop_production.sh"
    exit 1
fi

# 清理残留PID文件
[ -f "$PID_FILE" ] && rm -f $PID_FILE

# 检查依赖
echo "检查 Gunicorn 是否已安装..."
if ! command -v gunicorn &> /dev/null; then
    echo "正在安装 Gunicorn..."
    pip install gunicorn
fi

echo "检查 LibreOffice 是否已安装..."
if ! command -v soffice &> /dev/null; then
    echo "警告：LibreOffice 未安装，证书生成功能将不可用"
    echo "请运行：sudo apt install -y libreoffice"
fi

# 启动服务
echo "启动 PDF 证书管理系统（生产环境）..."
echo "工作进程数：$(python3 -c 'import multiprocessing; print(multiprocessing.cpu_count() * 2 + 1)')"
echo "访问地址：http://localhost:5000"
echo "管理后台：http://localhost:5000/admin"
echo ""

# 后台启动 Gunicorn
nohup gunicorn --config gunicorn_config.py wsgi:application > logs/app.log 2>&1 &
echo $! > $PID_FILE

# 等待启动完成
sleep 3

# 检查启动状态
if [ -f "$PID_FILE" ] && ps -p $(cat $PID_FILE) > /dev/null 2>&1; then
    PID=$(cat $PID_FILE)
    echo "✅ PDF证书管理系统启动成功！"
    echo "进程ID: $PID"
    echo "日志文件: logs/app.log"
    echo "访问日志: logs/gunicorn_access.log"
    echo "错误日志: logs/gunicorn_error.log"
    echo ""
    echo "停止服务请运行: ./stop_production.sh"
    echo "查看日志请运行: tail -f logs/app.log"
else
    echo "❌ 启动失败，请检查日志文件 logs/app.log"
    [ -f "$PID_FILE" ] && rm -f $PID_FILE
    exit 1
fi

 