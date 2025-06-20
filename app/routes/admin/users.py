from flask import render_template, request, jsonify
from datetime import datetime
from werkzeug.security import generate_password_hash
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

@admin_bp.route('/users')
@admin_login_required
def admin_users():
    """管理员管理页面"""
    admins = Admin.query.order_by(Admin.id).all()
    return render_template('admin/admins.html', admins=admins, active_page='admins')

@admin_bp.route('/user/add', methods=['POST'])
@admin_login_required
def admin_add_user():
    """添加管理员"""
    try:
        # 检查用户名是否已存在
        username = request.form.get('username')
        if Admin.query.filter_by(username=username).first():
            return jsonify({'error': '用户名已存在'})
        
        # 创建新管理员
        admin = Admin(
            username=username,
            password=generate_password_hash(request.form.get('password')),
            real_name=request.form.get('real_name'),
            email=request.form.get('email'),
            phone=request.form.get('phone'),
            status=int(request.form.get('status', 1)),
            create_time=datetime.now()
        )
        
        db.session.add(admin)
        db.session.commit()
        return jsonify({'message': '管理员添加成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@admin_bp.route('/user/<int:user_id>', methods=['GET'])
@admin_login_required
def admin_get_user(user_id):
    """获取管理员信息"""
    admin = Admin.query.get_or_404(user_id)
    return jsonify({
        'id': admin.id,
        'username': admin.username,
        'real_name': admin.real_name,
        'email': admin.email,
        'phone': admin.phone,
        'status': admin.status
    })

@admin_bp.route('/user/<int:user_id>', methods=['PUT'])
@admin_login_required
def admin_update_user(user_id):
    """更新管理员信息"""
    try:
        admin = Admin.query.get_or_404(user_id)
        
        # 检查用户名是否已被其他用户使用
        username = request.form.get('username')
        if username != admin.username and Admin.query.filter_by(username=username).first():
            return jsonify({'error': '用户名已存在'})
        
        # 更新信息
        admin.username = username
        admin.real_name = request.form.get('real_name')
        admin.email = request.form.get('email')
        admin.phone = request.form.get('phone')
        admin.status = int(request.form.get('status', 1))
        
        # 如果提供了新密码，则更新密码
        password = request.form.get('password')
        if password:
            admin.password = generate_password_hash(password)
        
        db.session.commit()
        return jsonify({'message': '管理员信息更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@admin_bp.route('/user/<int:user_id>', methods=['DELETE'])
@admin_login_required
def admin_delete_user(user_id):
    """删除管理员"""
    try:
        admin = Admin.query.get_or_404(user_id)
        
        # 不允许删除超级管理员
        if admin.username == 'admin':
            return jsonify({'error': '不能删除超级管理员账号'}), 400
        
        db.session.delete(admin)
        db.session.commit()
        return jsonify({'message': '管理员删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400 