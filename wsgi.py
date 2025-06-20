#!/usr/bin/env python3
"""
WSGI 入口文件
用于生产环境部署 PDF 证书管理系统
"""

import os
import sys
from app import create_app

# 添加项目路径到 Python 路径
sys.path.insert(0, os.path.dirname(__file__))

# 设置生产环境
os.environ.setdefault('FLASK_CONFIG', 'production')

# 创建应用实例
application = create_app('production')

if __name__ == "__main__":
    application.run() 