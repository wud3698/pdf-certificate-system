#!/usr/bin/env python3
"""
PDF证书管理系统后台运行入口文件
适用于后台运行，关闭了调试模式和自动重载
"""
import os
from app import create_app

# 获取配置环境
config_name = os.environ.get('FLASK_CONFIG', 'development')

# 创建应用实例
app = create_app(config_name)

if __name__ == '__main__':
    # 后台运行配置，关闭调试和重载
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=False,  # 关闭调试模式
        use_reloader=False,  # 关闭自动重载
        threaded=True  # 启用多线程
    ) 