from datetime import datetime
from . import db

class Admin(db.Model):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    real_name = db.Column(db.String(50))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    last_login_time = db.Column(db.DateTime)
    create_time = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.Integer, default=1)  # 1:启用 0:禁用 