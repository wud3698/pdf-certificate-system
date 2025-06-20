from app import app
from models import db, Admin
from datetime import datetime
from werkzeug.security import generate_password_hash

def init_admin():
    with app.app_context():
        # 检查是否已存在管理员账号
        admin = Admin.query.filter_by(username='admin').first()
        if not admin:
            # 创建默认管理员账号，使用加密密码
            admin = Admin(
                username='admin',
                password=generate_password_hash('admin123'),  # 使用加密密码
                real_name='系统管理员',
                email='admin@example.com',
                phone='13800138000',
                status=1,
                create_time=datetime.now()
            )
            db.session.add(admin)
            db.session.commit()
            print("默认管理员账号创建成功！")
        else:
            print("管理员账号已存在，无需创建。")

if __name__ == '__main__':
    init_admin() 