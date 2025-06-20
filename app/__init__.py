from flask import Flask
from flask_migrate import Migrate
import os
from datetime import datetime
from werkzeug.security import generate_password_hash

from app.models import db
from app.auth import auth_bp
from app.routes.admin import admin_bp, init_admin
from app.routes.main import main_bp
from app.services.certificate_generator import CertificateGenerator
from app.services.certificate_service import CertificateService
from app.models import Activity, Certificate, Admin
from app.config import config

def create_app(config_name='default'):
    """应用工厂函数"""
    # 获取项目根目录路径
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    
    # 创建Flask应用，指定模板和静态文件目录
    app = Flask(__name__, 
                template_folder=os.path.join(basedir, 'templates'),
                static_folder=os.path.join(basedir, 'static'))
    
    # 加载配置
    app.config.from_object(config[config_name])
    
    # 初始化扩展
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # 生产环境数据库连接优化
    if config_name == 'production':
        @app.teardown_appcontext
        def close_db(error):
            """请求结束后关闭数据库连接"""
            if hasattr(db, 'session'):
                db.session.remove()
        
        @app.before_request
        def before_request():
            """请求前检查数据库连接"""
            try:
                db.session.execute('SELECT 1')
            except Exception:
                db.session.rollback()
    
    # 创建上传目录
    _create_upload_directories(app)
    
    # 注册蓝图
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    
    # 初始化服务
    with app.app_context():
        db.create_all()
        
        # 自动创建默认管理员账号
        _create_default_admin()
        
        # 创建服务实例并注册到应用上下文
        app.certificate_generator = CertificateGenerator(app, db, Activity, Certificate)
        app.certificate_service = CertificateService(app, db, Activity, Certificate)
        
        # 初始化admin模块
        init_admin(app, app.certificate_generator, app.certificate_service)
    
    return app

def _create_default_admin():
    """自动创建默认管理员账号"""
    try:
        # 检查admin表中是否已存在任何管理员账号
        admin_count = Admin.query.count()
        if admin_count == 0:
            # 只有在admin表为空时才创建默认管理员账号
            admin = Admin(
                username='admin',
                password=generate_password_hash('admin123'),
                real_name='系统管理员',
                email='admin@example.com',
                phone='13800138000',
                status=1,
                create_time=datetime.now()
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ 默认管理员账号创建成功！")
            print("   用户名: admin")
            print("   密码: admin123")
            print("   请登录后及时修改密码！")
        else:
            print(f"ℹ️  admin表中已有 {admin_count} 个管理员账号，跳过创建")
    except Exception as e:
        print(f"⚠️  创建默认管理员账号失败: {e}")
        db.session.rollback()

def _create_upload_directories(app):
    """创建必要的上传目录"""
    directories = [
        app.config['UPLOAD_FOLDER'],
        app.config['CERTIFICATE_TEMPLATE_FOLDER'],
        app.config['GENERATED_CERTIFICATES_FOLDER'],
        app.config['ACTIVITY_IMAGES_FOLDER'],
        app.config['CAROUSEL_IMAGES_FOLDER'],
        app.config['PARTICIPANT_IMAGES_FOLDER']
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True) 