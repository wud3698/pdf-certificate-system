#!/bin/bash
# PDF证书管理系统生产环境停止脚本

PID_FILE="logs/gunicorn.pid"

echo "正在停止 PDF 证书管理系统..."

# 检查PID文件是否存在
if [ ! -f "$PID_FILE" ]; then
    echo "❌ 未找到PID文件，服务可能未运行"
    echo "尝试查找并停止所有Gunicorn进程..."
    
    # 查找所有相关进程
    PIDS=$(ps aux | grep -v grep | grep "gunicorn.*wsgi:application" | awk '{print $2}')
    
    if [ -z "$PIDS" ]; then
        echo "✅ 没有找到运行中的服务进程"
        exit 0
    else
        echo "找到进程: $PIDS"
        echo "正在停止所有相关进程..."
        echo "$PIDS" | xargs kill -TERM
        sleep 3
        
        # 检查是否还有残留进程
        REMAINING=$(ps aux | grep -v grep | grep "gunicorn.*wsgi:application" | awk '{print $2}')
        if [ ! -z "$REMAINING" ]; then
            echo "强制终止残留进程: $REMAINING"
            echo "$REMAINING" | xargs kill -9
        fi
        echo "✅ 所有进程已停止"
    fi
    exit 0
fi

# 读取PID
PID=$(cat $PID_FILE)

# 检查进程是否存在
if ! ps -p $PID > /dev/null 2>&1; then
    echo "❌ 进程 $PID 不存在，清理PID文件"
    rm -f $PID_FILE
    exit 0
fi

echo "停止进程 $PID..."

# 优雅停止
kill -TERM $PID

# 等待进程结束
echo "等待进程优雅退出..."
for i in {1..15}; do
    if ! ps -p $PID > /dev/null 2>&1; then
        echo "✅ 服务已停止"
        rm -f $PID_FILE
        exit 0
    fi
    echo -n "."
    sleep 1
done

echo ""
echo "进程未能优雅退出，强制终止..."

# 强制停止
kill -9 $PID

# 再次检查
if ps -p $PID > /dev/null 2>&1; then
    echo "❌ 无法停止进程 $PID"
    exit 1
else
    echo "✅ 服务已强制停止"
    rm -f $PID_FILE
fi

# 清理可能的残留进程
echo "检查并清理残留进程..."
REMAINING=$(ps aux | grep -v grep | grep "gunicorn.*wsgi:application" | awk '{print $2}')
if [ ! -z "$REMAINING" ]; then
    echo "发现残留进程: $REMAINING"
    echo "$REMAINING" | xargs kill -9
    echo "✅ 残留进程已清理"
fi

echo "🎯 PDF证书管理系统已完全停止" 