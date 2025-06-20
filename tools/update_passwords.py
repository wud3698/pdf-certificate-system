from app import app
from models import db, Admin
from werkzeug.security import generate_password_hash

def update_passwords():
    with app.app_context():
        admins = Admin.query.all()
        for admin in admins:
            if not admin.password.startswith('pbkdf2:sha256:'):
                admin.password = generate_password_hash(admin.password)
        db.session.commit()
        print("所有管理员密码已更新为加密格式！")

if __name__ == '__main__':
    update_passwords() 