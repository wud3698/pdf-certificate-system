#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Activity, Certificate, Admin, CarouselImage
from sqlalchemy import text

def update_database():
    """更新数据库结构"""
    app = create_app()
    
    with app.app_context():
        print("开始更新数据库...")
        
        # 创建所有表
        db.create_all()
        print("✅ 基础表结构创建完成")
        
        # 检查并添加新字段
        try:
            # 检查certificate表是否存在image_path_backup字段
            result = db.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'certificate' 
                AND COLUMN_NAME = 'image_path_backup'
            """)).fetchone()
            
            if not result:
                print("正在添加image_path_backup字段...")
                db.session.execute(text("""
                    ALTER TABLE certificate 
                    ADD COLUMN image_path_backup VARCHAR(200) COMMENT '备用图片路径'
                """))
                db.session.commit()
                print("✅ image_path_backup字段添加成功")
            else:
                print("✅ image_path_backup字段已存在")
                
        except Exception as e:
            print(f"⚠️  添加image_path_backup字段失败: {e}")
            
        # 其他现有的字段检查和更新逻辑...
        try:
            # 检查certificate表是否存在custom_fields字段
            result = db.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'certificate' 
                AND COLUMN_NAME = 'custom_fields'
            """)).fetchone()
            
            if not result:
                print("正在添加custom_fields字段...")
                db.session.execute(text("""
                    ALTER TABLE certificate 
                    ADD COLUMN custom_fields TEXT COMMENT 'JSON格式存储自定义字段'
                """))
                db.session.commit()
                print("✅ custom_fields字段添加成功")
            else:
                print("✅ custom_fields字段已存在")
                
        except Exception as e:
            print(f"⚠️  添加custom_fields字段失败: {e}")
            
        # 检查并修改cert_number字段为可空
        try:
            # 检查cert_number字段的约束
            result = db.session.execute(text("""
                SELECT IS_NULLABLE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'certificate' 
                AND COLUMN_NAME = 'cert_number'
            """)).fetchone()
            
            if result and result[0] == 'NO':
                print("正在修改cert_number字段为可空...")
                db.session.execute(text("""
                    ALTER TABLE certificate 
                    MODIFY COLUMN cert_number VARCHAR(50) NULL COMMENT '证书编号（可以为空）'
                """))
                db.session.commit()
                print("✅ cert_number字段修改为可空成功")
            else:
                print("✅ cert_number字段已是可空")
                
        except Exception as e:
            print(f"⚠️  修改cert_number字段失败: {e}")
            
        # 检查activity表的field_settings字段
        try:
            result = db.session.execute(text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'activity' 
                AND COLUMN_NAME = 'field_settings'
            """)).fetchone()
            
            if not result:
                print("正在添加field_settings字段...")
                db.session.execute(text("""
                    ALTER TABLE activity 
                    ADD COLUMN field_settings TEXT COMMENT '字段设置信息'
                """))
                db.session.commit()
                print("✅ field_settings字段添加成功")
            else:
                print("✅ field_settings字段已存在")
                
        except Exception as e:
            print(f"⚠️  添加field_settings字段失败: {e}")
            
        # 检查admin表并创建默认管理员
        try:
            admin_count = Admin.query.count()
            if admin_count == 0:
                print("创建默认管理员账号...")
                admin = Admin(
                    username='admin',
                    password='admin123'  # Admin模型会自动进行密码哈希
                )
                db.session.add(admin)
                db.session.commit()
                print("✅ 默认管理员账号创建成功")
                print("   用户名: admin")
                print("   密码: admin123")
                print("   ⚠️  请登录后立即修改密码!")
            else:
                print(f"✅ 管理员账号已存在 ({admin_count}个)")
                
        except Exception as e:
            print(f"⚠️  创建默认管理员账号失败: {e}")
            
        print("\n🎉 数据库更新完成!")
        print("请运行 python run.py 启动应用")

if __name__ == '__main__':
    update_database() 