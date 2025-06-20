#!/usr/bin/env python3
"""
PDF证书管理系统主入口文件
"""
import os
from app import create_app

# 获取配置环境
config_name = os.environ.get('FLASK_CONFIG', 'development')

# 创建应用实例
app = create_app(config_name)

if __name__ == '__main__':
    # 开发环境运行配置
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=app.config.get('DEBUG', False)
    ) 