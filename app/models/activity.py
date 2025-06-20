from datetime import datetime
import json
from . import db

class Activity(db.Model):
    __tablename__ = 'activity'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)  # 活动标题
    category = db.Column(db.String(50))  # 活动类别（综合、合唱等）
    region = db.Column(db.String(100))  # 区域（如：广州黄埔区）
    publisher = db.Column(db.String(100))  # 发布单位
    publish_date = db.Column(db.DateTime, default=datetime.now)  # 发布时间
    status = db.Column(db.String(20), default='草稿')  # 状态（草稿/列表公开/全部公开）
    template_file = db.Column(db.String(200))  # 证书模板文件路径
    template_type = db.Column(db.String(10))  # 模板类型（pdf/docx）
    image_file = db.Column(db.String(200))  # 活动图片文件路径
    _field_settings = db.Column('field_settings', db.Text)
    certificates = db.relationship('Certificate', backref='activity', lazy=True)

    @property
    def field_settings(self):
        if self._field_settings:
            return json.loads(self._field_settings)
        return {}

    @field_settings.setter
    def field_settings(self, value):
        if value is None:
            self._field_settings = None
        else:
            self._field_settings = json.dumps(value) 