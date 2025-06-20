from flask import Blueprint

# 创建主admin蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# 导入所有子模块
from . import auth, activities, certificates, generate, users, site, downloads

# 全局变量，将在应用初始化时设置
certificate_generator = None
certificate_service = None
app = None

def init_admin(flask_app, cert_gen, cert_service):
    """初始化admin模块"""
    global app, certificate_generator, certificate_service
    app = flask_app
    certificate_generator = cert_gen
    certificate_service = cert_service
    
    # 初始化各个子模块
    auth.init_module(flask_app, cert_gen, cert_service)
    activities.init_module(flask_app, cert_gen, cert_service)
    certificates.init_module(flask_app, cert_gen, cert_service)
    generate.init_module(flask_app, cert_gen, cert_service)
    users.init_module(flask_app, cert_gen, cert_service)
    site.init_module(flask_app, cert_gen, cert_service)
    downloads.init_module(flask_app, cert_gen, cert_service) 