import multiprocessing
import os

# 绑定地址和端口
bind = "0.0.0.0:5000"

# 工作进程数量 (CPU核心数 * 2 + 1)
workers = multiprocessing.cpu_count() * 2 + 1

# 工作进程类型
worker_class = "sync"

# 工作进程超时时间 (30分钟)
timeout = 1800

# 保持连接时间
keepalive = 2

# 最大并发请求数
max_requests = 1000

# 随机化请求数量，避免同时重启
max_requests_jitter = 100

# 预加载应用
preload_app = True

# 日志配置
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"

# 进程名称
proc_name = "pdf_certificate_system"

# 用户和组（如果需要）
# user = "www-data"
# group = "www-data"

# PID文件
pidfile = "logs/gunicorn.pid"

# 守护进程模式
daemon = False

# 重新加载代码（生产环境建议关闭）
reload = False 