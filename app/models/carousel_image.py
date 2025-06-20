from datetime import datetime
from . import db

class CarouselImage(db.Model):
    """首页轮播图"""
    __tablename__ = 'carousel_image'
    id = db.Column(db.Integer, primary_key=True)
    image_file = db.Column(db.String(255), nullable=False)  # 图片文件路径
    order = db.Column(db.Integer, default=1)  # 显示顺序
    create_time = db.Column(db.DateTime, default=datetime.now)  # 创建时间 