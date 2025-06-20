#!/bin/bash
# PDF证书管理系统生产环境启动脚本（前台运行）

# 设置环境变量
export FLASK_CONFIG=production
export PYTHONPATH=/www/pdf:$PYTHONPATH

# 创建必要的目录
mkdir -p logs
mkdir -p uploads/temp

# 检查依赖
echo "检查 Gunicorn 是否已安装..."
if ! command -v gunicorn &> /dev/null; then
    echo "正在安装 Gunicorn..."
    pip install --break-system-packages gunicorn
fi

echo "检查 LibreOffice 是否已安装..."
if ! command -v soffice &> /dev/null; then
    echo "警告：LibreOffice 未安装，证书生成功能将不可用"
    echo "请运行：sudo apt install -y libreoffice"
fi

# 显示启动信息
echo "启动 PDF 证书管理系统（生产环境）..."
echo "工作进程数：$(python3 -c 'import multiprocessing; print(multiprocessing.cpu_count() * 2 + 1)')"
echo "访问地址：http://localhost:5000"
echo "管理后台：http://localhost:5000/admin"
echo "运行模式：前台运行（按 Ctrl+C 停止）"
echo ""

# 前台启动 Gunicorn
gunicorn --config gunicorn_config.py wsgi:application 