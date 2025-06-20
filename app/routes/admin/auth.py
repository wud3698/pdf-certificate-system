from flask import render_template, request, redirect, url_for, session
from datetime import datetime
from werkzeug.security import check_password_hash
from app.models import db, Admin
from app.auth import admin_login_required
from . import admin_bp

# 全局变量
app = None
certificate_generator = None
certificate_service = None

def init_module(flask_app, cert_gen, cert_service):
    """初始化模块"""
    global app, certificate_generator, certificate_service
    app = flask_app
    certificate_generator = cert_gen
    certificate_service = cert_service

@admin_bp.route('/')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth.admin_login'))
    return redirect(url_for('admin.admin_activities'))

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(username=username).first()
        
        # 验证密码和账号状态
        is_valid = (admin and check_password_hash(admin.password, password) and admin.status == 1)
        
        if is_valid:
            # 更新最后登录时间
            admin.last_login_time = datetime.now()
            db.session.commit()
            
            session['admin_logged_in'] = True
            session['admin_id'] = admin.id
            session['admin_username'] = admin.username
            session['admin_real_name'] = admin.real_name
            
            return redirect(url_for('admin.admin_activities'))
        else:
            return render_template('admin/login.html', error='用户名或密码错误，或账号已被禁用')
    
    return render_template('admin/login.html')

@admin_bp.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin.login')) 