import os
from datetime import timedelta

class Config:
    """基础配置类"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    
    # 文件上传配置
    UPLOAD_FOLDER = 'uploads'
    CERTIFICATE_TEMPLATE_FOLDER = os.path.join('uploads', 'templates')
    GENERATED_CERTIFICATES_FOLDER = os.path.join('uploads', 'certificates')
    ACTIVITY_IMAGES_FOLDER = os.path.join('uploads', 'images')
    CAROUSEL_IMAGES_FOLDER = os.path.join('uploads', 'carousel')
    PARTICIPANT_IMAGES_FOLDER = os.path.join('uploads', 'participant_images')

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'mysql+pymysql://root:12345@192.168.9.102/pdf123'

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://root:12345@192.168.9.102/pdf123'
    
    # 生产环境数据库连接池配置 - 解决多进程连接问题
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 20,                    # 连接池大小
        'max_overflow': 30,                 # 最大溢出连接数
        'pool_timeout': 30,                 # 获取连接超时时间
        'pool_recycle': 3600,               # 连接回收时间（1小时）
        'pool_pre_ping': True,              # 连接前ping测试
        'connect_args': {
            'charset': 'utf8mb4',
            'connect_timeout': 60,          # 连接超时
            'read_timeout': 600,            # 读取超时
            'write_timeout': 600,           # 写入超时
            'autocommit': True,             # 自动提交
            'use_unicode': True,            # 使用Unicode
        }
    }

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 