from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from functools import wraps
from app.models import Certificate, Admin, db
from datetime import datetime
from werkzeug.security import check_password_hash

# 创建蓝图
auth_bp = Blueprint('auth', __name__)

def login_required(view_func):
    """登录验证装饰器"""
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        activity_id = kwargs.get('activity_id')
        if not activity_id:
            return redirect(url_for('main.index'))
            
        auth_key = f'authenticated_{activity_id}'
        if not session.get(auth_key):
            return redirect(url_for('main.activity_detail', activity_id=activity_id))
        
        # 验证用户是否有权限访问该单位的证书
        if kwargs.get('unit_name') and session.get(f'unit_name_{activity_id}') != kwargs.get('unit_name'):
            return redirect(url_for('main.activity_detail', activity_id=activity_id))
            
        return view_func(*args, **kwargs)
    
    return wrapped_view

def admin_login_required(view_func):
    """管理员登录验证装饰器"""
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('auth.admin_login'))
        return view_func(*args, **kwargs)
    return wrapped_view

@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = Admin.query.filter_by(username=username).first()
        
        if not admin:
            return render_template('admin/login.html', error='用户名或密码错误，或账号已被禁用')
            
        # 验证密码
        try:
            # 尝试使用加密验证
            is_valid = check_password_hash(admin.password, password)
        except Exception as e:
            # 如果加密验证失败，尝试明文比较
            is_valid = (admin.password == password)
        
        if is_valid and admin.status == 1:
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

@auth_bp.route('/admin/logout')
def admin_logout():
    """管理员退出登录"""
    session.pop('admin_logged_in', None)
    session.pop('admin_id', None)
    session.pop('admin_username', None)
    session.pop('admin_real_name', None)
    return redirect(url_for('auth.admin_login'))

@auth_bp.route('/verify_certificate_access', methods=['POST'])
def verify_certificate_access():
    try:
        unit_name = request.form.get('unit_name')
        id_number = request.form.get('id_number')
        name = request.form.get('name')
        current_unit = request.form.get('current_unit')
        activity_id = request.form.get('activity_id')
        
        print(f"收到登录请求: activity_id={activity_id}, unit_name={unit_name}, name={name}, id_number={id_number}")  # 调试日志
        
        if not all([unit_name, id_number, name, current_unit, activity_id]):
            print(f"缺少必要信息: unit_name={unit_name}, id_number={id_number}, name={name}, current_unit={current_unit}, activity_id={activity_id}")  # 调试日志
            return jsonify({
                'success': False,
                'message': '请填写所有必填信息'
            })

        # 验证用户信息，考虑身份证号可能有空格的情况
        cert = Certificate.query.filter(
            Certificate.activity_id == activity_id,
            Certificate.unit_name == current_unit,
            Certificate.name == name
        ).filter(
            db.func.trim(Certificate.id_number) == id_number.strip()
        ).first()
        
        if not cert:
            print(f"未找到匹配的证书: activity_id={activity_id}, unit_name={current_unit}, id_number={id_number}, name={name}")  # 调试日志
            return jsonify({
                'success': False,
                'message': '未找到匹配的证书信息，请检查填写的信息是否正确'
            })
            
        if cert.unit_name != unit_name:
            print(f"单位名称不匹配: 输入={unit_name}, 证书={cert.unit_name}")  # 调试日志
            return jsonify({
                'success': False,
                'message': '单位名称与证书不匹配'
            })

        # 创建活动特定的会话数据
        auth_key = f'authenticated_{activity_id}'
        session[auth_key] = True
        session[f'unit_name_{activity_id}'] = unit_name
        session[f'name_{activity_id}'] = name
        session[f'id_number_{activity_id}'] = id_number
        
        # 确保会话数据被保存
        session.modified = True
        
        print(f"登录成功: auth_key={auth_key}, session数据={dict(session)}")  # 调试日志
        
        return jsonify({
            'success': True,
            'message': '登录成功'
        })
        
    except Exception as e:
        print(f"登录错误: {str(e)}")  # 调试日志
        return jsonify({
            'success': False,
            'message': '登录过程中发生错误，请稍后重试'
        })

@auth_bp.route('/logout')
def logout():
    """退出登录"""
    activity_id = request.args.get('activity_id')
    if activity_id:
        # 清除特定活动的会话数据
        auth_key = f'authenticated_{activity_id}'
        session.pop(auth_key, None)
        session.pop(f'unit_name_{activity_id}', None)
        session.pop(f'name_{activity_id}', None)
        session.pop(f'phone_{activity_id}', None)
    return redirect(url_for('main.activity_detail', activity_id=activity_id)) 