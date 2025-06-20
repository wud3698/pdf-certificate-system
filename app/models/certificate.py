from datetime import datetime
from . import db

class Certificate(db.Model):
    __tablename__ = 'certificate'
    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activity.id'), nullable=False)  # 关联活动
    cert_number = db.Column(db.String(50), nullable=True)  # 证书编号（可以为空）
    unit_name = db.Column(db.String(100), nullable=False)  # 单位名称
    area = db.Column(db.String(100))  # 所属区域
    name = db.Column(db.String(50), nullable=False)  # 姓名
    id_type = db.Column(db.String(20))  # 证件类型
    id_number = db.Column(db.String(50))  # 证件号
    gender = db.Column(db.String(10))  # 性别
    age = db.Column(db.Integer)  # 年龄
    birth_date = db.Column(db.Date)  # 出生日期
    phone = db.Column(db.String(20))  # 手机号
    identity = db.Column(db.String(50))  # 身份
    grade_major = db.Column(db.String(100))  # 年级专业
    image_path = db.Column(db.String(200))  # 图片路径
    image_path_backup = db.Column(db.String(200))  # 备用图片路径
    project = db.Column(db.String(100))  # 参赛项目
    param_group = db.Column(db.String(50))  # 参数组别
    certificate_file = db.Column(db.String(200))  # 证书文件路径
    custom_fields = db.Column(db.Text)  # JSON格式存储自定义字段
    create_time = db.Column(db.DateTime, default=datetime.now)
    
    # 注意：移除了唯一约束，因为证书编号现在可以为空
    # 如果需要约束，可以考虑在应用层面处理非空证书编号的唯一性 