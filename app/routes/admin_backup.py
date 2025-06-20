from flask import Blueprint, render_template, request, jsonify, send_file, redirect, url_for, session, flash
import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db, Activity, Certificate, Admin, CarouselImage
from app.services.certificate_generator import CertificateGenerator
from app.services.certificate_service import CertificateService
from app.auth import admin_login_required
import zipfile
from io import BytesIO

# 创建蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# 全局变量，将在应用初始化时设置
certificate_generator = None
certificate_service = None
app = None

# 管理员账号信息（实际应用中应该存储在数据库中并加密密码）
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def init_admin(flask_app, cert_gen, cert_service):
    """初始化admin模块"""
    global app, certificate_generator, certificate_service
    app = flask_app
    certificate_generator = cert_gen
    certificate_service = cert_service

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

@admin_bp.route('/activities')
@admin_login_required
def admin_activities():
    # 获取搜索参数
    title = request.args.get('title', '')
    category = request.args.get('category', '')
    region = request.args.get('region', '')
    publisher = request.args.get('publisher', '')
    status = request.args.get('status', '')

    # 构建查询
    query = Activity.query
    if title:
        query = query.filter(Activity.title.like(f'%{title}%'))
    if category:
        query = query.filter(Activity.category.like(f'%{category}%'))
    if region:
        query = query.filter(Activity.region.like(f'%{region}%'))
    if publisher:
        query = query.filter(Activity.publisher.like(f'%{publisher}%'))
    if status:
        query = query.filter(Activity.status == status)

    # 按发布时间升序排列
    activities = query.order_by(Activity.publish_date.asc()).all()
    return render_template('admin/activities.html', activities=activities, active_page='activities')

@admin_bp.route('/upload')
@admin_login_required
def admin_upload():
    activities = Activity.query.order_by(Activity.publish_date.desc()).all()
    return render_template('admin/upload.html', activities=activities, active_page='upload')

@admin_bp.route('/activity/add', methods=['POST'])
@admin_login_required
def admin_add_activity():
    try:
        # 处理图片上传
        image_file = request.files.get('image')
        image_path = None
        
        if image_file and image_file.filename:
            # 验证文件类型
            allowed_extensions = {'jpg', 'jpeg', 'png'}
            file_ext = os.path.splitext(image_file.filename)[1].lower()
            if file_ext[1:] not in allowed_extensions:
                return jsonify({'error': '只支持jpg、jpeg、png格式的图片'}), 400
            
            # 生成安全的文件名并保存
            filename = secure_filename(f'activity_{datetime.now().strftime("%Y%m%d%H%M%S")}{file_ext}')
            image_path = os.path.join(app.config['ACTIVITY_IMAGES_FOLDER'], filename)
            image_file.save(image_path)

        activity = Activity(
            title=request.form['title'],
            category=request.form['category'],
            region=request.form['region'],
            publisher=request.form['publisher'],
            status=request.form['status'],
            image_file=image_path
        )
        db.session.add(activity)
        db.session.commit()
        return jsonify({'message': '活动添加成功', 'id': activity.id})
    except Exception as e:
        db.session.rollback()
        # 如果图片已保存但数据库操作失败，删除已保存的图片
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
        return jsonify({'error': str(e)}), 400

@admin_bp.route('/activity/<int:activity_id>', methods=['PUT'])
@admin_login_required
def admin_update_activity(activity_id):
    try:
        activity = Activity.query.get_or_404(activity_id)
        old_image = activity.image_file
        
        # 处理图片上传
        image_file = request.files.get('image')
        if image_file and image_file.filename:
            # 验证文件类型
            allowed_extensions = {'jpg', 'jpeg', 'png'}
            file_ext = os.path.splitext(image_file.filename)[1].lower()
            if file_ext[1:] not in allowed_extensions:
                return jsonify({'error': '只支持jpg、jpeg、png格式的图片'}), 400
            
            # 生成安全的文件名并保存
            filename = secure_filename(f'activity_{activity_id}_{datetime.now().strftime("%Y%m%d%H%M%S")}{file_ext}')
            image_path = os.path.join(app.config['ACTIVITY_IMAGES_FOLDER'], filename)
            image_file.save(image_path)
            
            # 更新图片路径
            activity.image_file = image_path
            
            # 删除旧图片
            if old_image and os.path.exists(old_image):
                os.remove(old_image)

        activity.title = request.form['title']
        activity.category = request.form['category']
        activity.region = request.form['region']
        activity.publisher = request.form['publisher']
        activity.status = request.form['status']
        
        db.session.commit()
        return jsonify({'message': '活动更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@admin_bp.route('/activity/<int:activity_id>', methods=['DELETE'])
@admin_login_required
def admin_delete_activity(activity_id):
    try:
        activity = Activity.query.get_or_404(activity_id)
        
        # 检查是否存在关联的证书
        certificates = Certificate.query.filter_by(activity_id=activity_id).first()
        if certificates:
            return jsonify({'error': 'has_certificates'}), 400
        
        # 删除活动图片
        if activity.image_file and os.path.exists(activity.image_file):
            os.remove(activity.image_file)
            
        db.session.delete(activity)
        db.session.commit()
        return jsonify({'message': '活动删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@admin_bp.route('/activity/<int:activity_id>/image')
def get_activity_image(activity_id):
    """获取活动图片"""
    activity = Activity.query.get_or_404(activity_id)
    if not activity.image_file or not os.path.exists(activity.image_file):
        return '', 404
    return send_file(activity.image_file)

@admin_bp.route('/certificates')
@admin_login_required
def admin_certificates():
    # 如果没有选择活动，重定向到活动列表页面
    return redirect(url_for('admin.admin_activities'))

@admin_bp.route('/certificates/<int:activity_id>')
@admin_login_required
def admin_certificates_by_activity(activity_id):
    # 获取活动信息
    activity = Activity.query.get_or_404(activity_id)
    
    # 获取搜索参数
    cert_number = request.args.get('cert_number', '')
    unit_name = request.args.get('unit_name', '')
    group = request.args.get('group', '')
    athlete_name = request.args.get('athlete_name', '')
    phone = request.args.get('phone', '')
    
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50000, type=int)
    
    # 限制每页显示数量，防止过大
    if per_page > 50000:
        per_page = 50000
    elif per_page < 10:
        per_page = 10

    # 构建查询
    query = Certificate.query.filter_by(activity_id=activity_id)
    if cert_number:
        query = query.filter(Certificate.cert_number.like(f'%{cert_number}%'))
    if unit_name:
        query = query.filter(Certificate.unit_name.like(f'%{unit_name}%'))
    if group:
        query = query.filter(Certificate.param_group.like(f'%{group}%'))
    if athlete_name:
        query = query.filter(Certificate.name.like(f'%{athlete_name}%'))
    if phone:
        query = query.filter(Certificate.phone.like(f'%{phone}%'))

    # 应用分页
    if per_page >= 50000:
        # 显示全部，不使用分页
        certificates = query.order_by(Certificate.id.desc()).all()
        # 创建一个模拟的分页对象用于模板渲染
        class MockPagination:
            def __init__(self, items):
                self.items = items
                self.total = len(items)
                self.page = 1
                self.pages = 1
                self.per_page = len(items)
                self.has_prev = False
                self.has_next = False
                self.prev_num = None
                self.next_num = None
                
            def iter_pages(self, left_edge=1, right_edge=1, left_current=2, right_current=2):
                return [1]
        
        pagination = MockPagination(certificates)
    else:
        # 正常分页
        pagination = query.order_by(Certificate.id.desc()).paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        certificates = pagination.items

    return render_template('admin/certificates.html', 
                         certificates=certificates, 
                         pagination=pagination,
                         activity=activity, 
                         active_page='certificates')

@admin_bp.route('/certificate/<int:cert_id>', methods=['DELETE'])
@admin_login_required
def admin_delete_certificate(cert_id):
    try:
        cert = Certificate.query.get_or_404(cert_id)
        
        # 删除相关文件
        files_to_delete = []
        if cert.certificate_file and os.path.exists(cert.certificate_file):
            files_to_delete.append(cert.certificate_file)
        
        if cert.image_path and os.path.exists(cert.image_path):
            files_to_delete.append(cert.image_path)
        
        # 先删除数据库记录
        db.session.delete(cert)
        db.session.commit()
        
        # 然后删除文件（即使文件删除失败，数据库记录也已经删除）
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
            except OSError as e:
                # 记录文件删除失败，但不影响整体操作
                print(f"警告：删除文件失败 {file_path}: {e}")
        
        return jsonify({'message': '证书删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@admin_bp.route('/certificate/<int:cert_id>', methods=['PUT'])
@admin_login_required
def admin_update_certificate(cert_id):
    try:
        cert = Certificate.query.get_or_404(cert_id)
        data = request.get_json()
        
        # 更新证书信息
        cert.cert_number = data.get('cert_number', cert.cert_number)
        cert.unit_name = data.get('unit_name', cert.unit_name)
        cert.param_group = data.get('param_group', cert.param_group)
        cert.project = data.get('project', cert.project)
        cert.name = data.get('name', cert.name)
        cert.phone = data.get('phone', cert.phone)
        
        # 如果证书已生成，删除旧的证书文件
        if cert.certificate_file and os.path.exists(cert.certificate_file):
            os.remove(cert.certificate_file)
            cert.certificate_file = None
        
        db.session.commit()
        return jsonify({'message': '证书更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@admin_bp.route('/generate', methods=['GET', 'POST'])
@admin_login_required
def admin_generate():
    if request.method == 'GET':
        activities = Activity.query.order_by(Activity.publish_date.desc()).all()
        return render_template('admin/generate.html', 
                            activities=activities, 
                            winners=[],
                            active_page='generate')
    else:
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'error': '无效的请求数据', 'success': False}), 400
                
            activity_id = data.get('activity_id')
            if not activity_id:
                return jsonify({'error': '未指定活动', 'success': False}), 400
                
            activity = Activity.query.get(activity_id)
            if not activity:
                return jsonify({'error': '活动不存在', 'success': False}), 404
            
            if not activity.template_file or not os.path.exists(activity.template_file):
                return jsonify({'error': '证书模板不存在', 'success': False}), 404
            
            if activity.template_type != 'docx':
                return jsonify({'error': '只支持DOCX格式的证书模板', 'success': False}), 400
            
            generate_all = data.get('generate_all', False)
            winner_ids = data.get('winner_ids') if not generate_all else None
            image_size = data.get('image_size', 'one_inch')  # 获取图片尺寸参数，默认为一寸
            backup_image_size = data.get('backup_image_size', 'square_small')  # 获取备用图片尺寸参数，默认为正方形小
            
            # 获取需要生成证书的获奖者
            query = Certificate.query.filter_by(activity_id=activity_id)
            if not generate_all and winner_ids:
                query = query.filter(Certificate.id.in_(winner_ids))
            
            certificates = query.all()
            
            if not certificates:
                return jsonify({
                    'message': '没有找到需要生成证书的获奖者',
                    'success': False
                }), 404
            
            success_count = 0
            error_messages = []
            
            for cert in certificates:
                try:
                    # 如果已存在证书文件，先删除
                    if cert.certificate_file and os.path.exists(cert.certificate_file):
                        os.remove(cert.certificate_file)
                    
                    cert_data = {
                        'cert_number': cert.cert_number,
                        'unit_name': cert.unit_name,
                        'param_group': cert.param_group,
                        'project': cert.project,
                        'name': cert.name,
                        'phone': cert.phone,
                        'area': cert.area,
                        'id_type': cert.id_type,
                        'id_number': cert.id_number,
                        'gender': cert.gender,
                        'age': cert.age,
                        'birth_date': cert.birth_date,
                        'identity': cert.identity,
                        'grade_major': cert.grade_major,
                        'image_path': cert.image_path,
                        'image_path_backup': cert.image_path_backup
                    }
                    
                    result = certificate_generator.generate_certificate(activity_id, cert_data, image_size, backup_image_size)
                    
                    if result.get('success'):
                        cert.certificate_file = os.path.join('uploads', 'certificates', result.get('filename'))
                        db.session.commit()
                        success_count += 1
                    else:
                        error_message = f'{cert.name or cert.unit_name}: {result.get("error", "未知错误")}'
                        error_messages.append(error_message)
                except Exception as e:
                    error_message = f'{cert.name or cert.unit_name}: {str(e)}'
                    error_messages.append(error_message)
            
            if error_messages:
                return jsonify({
                    'message': f'部分证书生成失败。成功：{success_count}份，失败：{len(error_messages)}份',
                    'errors': error_messages,
                    'success': False
                }), 500
            
            return jsonify({
                'message': f'成功生成 {success_count} 份证书',
                'success': True
            })
            
        except Exception as e:
            app.logger.error(f'生成证书时发生错误: {str(e)}', exc_info=True)
            return jsonify({
                'message': f'生成证书时发生错误: {str(e)}',
                'success': False
            }), 500

@admin_bp.route('/certificate/<int:cert_id>/file', methods=['DELETE'])
@admin_login_required
def admin_delete_certificate_file(cert_id):
    try:
        cert = Certificate.query.get_or_404(cert_id)
        
        if not cert.certificate_file:
            return jsonify({'error': '证书文件不存在'}), 404
            
        if os.path.exists(cert.certificate_file):
            os.remove(cert.certificate_file)
            
        cert.certificate_file = None
        db.session.commit()
        
        return jsonify({'message': '证书文件删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

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

@admin_bp.route('/activity/<int:activity_id>/certificate', methods=['POST'])
@admin_login_required
def admin_add_certificate(activity_id):
    try:
        # 获取活动信息
        activity = Activity.query.get_or_404(activity_id)
        
        # 获取请求数据
        data = request.get_json()
        
        # 创建新证书
        certificate = Certificate(
            activity_id=activity_id,
            cert_number=data.get('cert_number'),
            unit_name=data.get('unit_name'),
            param_group=data.get('param_group'),
            project=data.get('project'),
            name=data.get('name'),
            phone=data.get('phone'),
            area=data.get('area'),
            id_type=data.get('id_type'),
            id_number=data.get('id_number'),
            gender=data.get('gender'),
            age=data.get('age'),
            birth_date=data.get('birth_date'),
            identity=data.get('identity'),
            grade_major=data.get('grade_major'),
            image_path=data.get('image_path'),
            image_path_backup=data.get('image_path_backup')
        )
        
        db.session.add(certificate)
        db.session.commit()
        
        return jsonify({
            'message': '证书添加成功',
            'id': certificate.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@admin_bp.route('/site')
@admin_login_required
def site_settings():
    # 获取所有轮播图，按order排序
    carousel_images = CarouselImage.query.order_by(CarouselImage.order).all()
    
    # 处理图片URL
    images = []
    for img in carousel_images:
        images.append({
            'id': img.id,
            'url': url_for('main.get_carousel_image', image_id=img.id),
            'order': img.order
        })
    
    # 检查帮助文档是否存在
    help_pdf_path = os.path.join('static', 'help.pdf')
    help_pdf_url = url_for('static', filename='help.pdf') if os.path.exists(help_pdf_path) else None
    
    return render_template('admin/site.html', 
                         carousel_images=images,
                         help_pdf_url=help_pdf_url,
                         active_page='site')

@admin_bp.route('/site/upload-carousel', methods=['POST'])
@admin_login_required
def upload_carousel_image():
    if 'carousel_image' not in request.files:
        flash('没有选择文件', 'error')
        return redirect(url_for('admin.site_settings'))
    
    file = request.files['carousel_image']
    if file.filename == '':
        flash('没有选择文件', 'error')
        return redirect(url_for('admin.site_settings'))
    
    if file and allowed_file(file.filename):
        # 生成文件名
        filename = secure_filename(f'carousel_{datetime.now().strftime("%Y%m%d%H%M%S")}{os.path.splitext(file.filename)[1]}')
        file_path = os.path.join(app.config['CAROUSEL_IMAGES_FOLDER'], filename)
        
        # 保存文件
        file.save(file_path)
        
        # 创建数据库记录
        image = CarouselImage(
            image_file=file_path,
            order=request.form.get('image_order', type=int, default=1)
        )
        db.session.add(image)
        db.session.commit()
        
        flash('图片上传成功', 'success')
    else:
        flash('不支持的文件格式', 'error')
    
    return redirect(url_for('admin.site_settings'))

@admin_bp.route('/site/delete-carousel', methods=['POST'])
@admin_login_required
def delete_carousel_image():
    image_id = request.form.get('image_id', type=int)
    if not image_id:
        flash('参数错误', 'error')
        return redirect(url_for('admin.site_settings'))
    
    image = CarouselImage.query.get_or_404(image_id)
    
    # 删除文件
    if image.image_file and os.path.exists(image.image_file):
        os.remove(image.image_file)
    
    # 删除数据库记录
    db.session.delete(image)
    db.session.commit()
    
    flash('图片删除成功', 'success')
    return redirect(url_for('admin.site_settings'))

@admin_bp.route('/site/upload-help-pdf', methods=['POST'])
@admin_login_required
def upload_help_pdf():
    try:
        if 'help_pdf' not in request.files:
            flash('没有选择文件', 'error')
            return redirect(url_for('admin.site_settings'))
        
        file = request.files['help_pdf']
        if file.filename == '':
            flash('没有选择文件', 'error')
            return redirect(url_for('admin.site_settings'))
        
        if file and file.filename.lower().endswith('.pdf'):
            # 确保static目录存在
            if not os.path.exists('static'):
                os.makedirs('static')
            
            # 保存文件
            file_path = os.path.join('static', 'help.pdf')
            
            # 如果已存在旧文件，先删除
            if os.path.exists(file_path):
                os.remove(file_path)
            
            file.save(file_path)
            flash('帮助文档上传成功', 'success')
        else:
            flash('只允许上传PDF文件', 'error')
            
        return redirect(url_for('admin.site_settings'))
    except Exception as e:
        flash(f'上传失败：{str(e)}', 'error')
        return redirect(url_for('admin.site_settings'))

@admin_bp.route('/site/delete-help-pdf', methods=['POST'])
@admin_login_required
def delete_help_pdf():
    try:
        file_path = os.path.join('static', 'help.pdf')
        if os.path.exists(file_path):
            os.remove(file_path)
            flash('帮助文档删除成功', 'success')
        else:
            flash('帮助文档不存在', 'error')
        
        return redirect(url_for('admin.site_settings'))
    except Exception as e:
        flash(f'删除失败：{str(e)}', 'error')
        return redirect(url_for('admin.site_settings'))

@admin_bp.route('/download/selected', methods=['POST'])
@admin_login_required
def admin_download_selected_certificates():
    """下载选中的证书"""
    try:
        data = request.get_json()
        cert_ids = data.get('cert_ids', [])
        
        if not cert_ids:
            return jsonify({'error': '未选择任何证书'}), 400
        
        # 获取选中的证书
        certificates = Certificate.query.filter(Certificate.id.in_(cert_ids)).all()
        
        if not certificates:
            return jsonify({'error': '未找到证书'}), 404
        
        # 检查是否所有证书都有文件
        valid_certs = []
        for cert in certificates:
            if cert.certificate_file and os.path.exists(cert.certificate_file):
                valid_certs.append(cert)
        
        if not valid_certs:
            return jsonify({'error': '所选证书均未生成文件'}), 404
        
        # 如果只有一个证书，直接下载
        if len(valid_certs) == 1:
            cert = valid_certs[0]
            # 生成新文件名：单位+组别+项目+获奖名次
            filename = _generate_certificate_filename(cert)
            return send_file(
                cert.certificate_file,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename
            )
        
        # 多个证书打包下载 - 使用流式压缩提高性能
        def generate_zip():
            memory_file = BytesIO()
            with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
                for cert in valid_certs:
                    try:
                        # 生成新文件名：单位+组别+项目+获奖名次
                        filename = _generate_certificate_filename(cert)
                        # 检查文件是否重名，如果重名则添加序号
                        counter = 1
                        original_filename = filename
                        while filename in [info.filename for info in zf.filelist]:
                            name, ext = os.path.splitext(original_filename)
                            filename = f"{name}_{counter}{ext}"
                            counter += 1
                        
                        zf.write(cert.certificate_file, filename)
                    except Exception as e:
                        app.logger.warning(f'添加证书文件失败 {cert.id}: {str(e)}')
                        continue
            
            memory_file.seek(0)
            return memory_file
        
        zip_file = generate_zip()
        
        # 获取活动名称作为压缩包名称
        activity = certificates[0].activity if certificates else None
        zip_name = f'{activity.title}_选中证书.zip' if activity else '选中证书.zip'
        
        return send_file(
            zip_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_name
        )
        
    except Exception as e:
        app.logger.error(f'下载选中证书失败: {str(e)}')
        return jsonify({'error': f'下载失败: {str(e)}'}), 500

@admin_bp.route('/download/all/<int:activity_id>')
@admin_login_required
def admin_download_all_certificates(activity_id):
    """下载活动的全部证书 - 优化版本"""
    try:
        # 获取活动信息
        activity = Activity.query.get_or_404(activity_id)
        
        # 获取所有已生成的证书
        certificates = Certificate.query.filter_by(activity_id=activity_id).all()
        
        if not certificates:
            return jsonify({'error': '该活动暂无证书'}), 404
        
        # 筛选有文件的证书
        valid_certs = []
        for cert in certificates:
            if cert.certificate_file and os.path.exists(cert.certificate_file):
                valid_certs.append(cert)
        
        if not valid_certs:
            return jsonify({'error': '该活动暂无已生成的证书文件'}), 404
        
        # 如果证书数量很多，建议分批下载
        if len(valid_certs) > 100:
            return jsonify({
                'error': f'证书数量过多({len(valid_certs)}份)，建议使用选中下载功能分批下载',
                'suggestion': 'batch_download'
            }), 400
        
        # 使用生成器函数创建ZIP文件，提高内存效率
        def generate_zip():
            memory_file = BytesIO()
            with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as zf:
                processed = 0
                for cert in valid_certs:
                    try:
                        # 生成新文件名：单位+组别+项目+获奖名次
                        filename = _generate_certificate_filename(cert)
                        # 检查文件是否重名，如果重名则添加序号
                        counter = 1
                        original_filename = filename
                        while filename in [info.filename for info in zf.filelist]:
                            name, ext = os.path.splitext(original_filename)
                            filename = f"{name}_{counter}{ext}"
                            counter += 1
                        
                        zf.write(cert.certificate_file, filename)
                        processed += 1
                        
                        # 记录进度（可用于后续添加进度条）
                        if processed % 10 == 0:
                            app.logger.info(f'打包进度: {processed}/{len(valid_certs)}')
                            
                    except Exception as e:
                        app.logger.warning(f'添加证书文件失败 {cert.id}: {str(e)}')
                        continue
            
            memory_file.seek(0)
            return memory_file
        
        zip_file = generate_zip()
        zip_name = f'{activity.title}_全部证书.zip'
        
        return send_file(
            zip_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_name
        )
        
    except Exception as e:
        app.logger.error(f'下载全部证书失败: {str(e)}')
        return jsonify({'error': f'下载失败: {str(e)}'}), 500

@admin_bp.route('/download/progress/<int:activity_id>')
@admin_login_required
def get_download_progress(activity_id):
    """获取下载进度（为将来的进度条功能预留）"""
    try:
        # 这里可以实现下载进度查询
        # 目前返回证书数量信息
        total_certs = Certificate.query.filter_by(activity_id=activity_id).count()
        valid_certs = Certificate.query.filter_by(activity_id=activity_id).filter(
            Certificate.certificate_file.isnot(None)
        ).count()
        
        return jsonify({
            'total': total_certs,
            'valid': valid_certs,
            'ready': valid_certs > 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def _generate_certificate_filename(cert):
    """生成证书文件名：单位+组别+项目+获奖名次.pdf"""
    parts = []
    
    # 单位名称
    if cert.unit_name:
        parts.append(cert.unit_name.strip())
    
    # 组别
    if cert.param_group:
        parts.append(cert.param_group.strip())
    
    # 项目
    if cert.project:
        parts.append(cert.project.strip())
    
    # 姓名（如果有的话）
    if cert.name:
        parts.append(cert.name.strip())
    
    # 如果没有任何有效部分，使用证书编号或默认名称
    if not parts:
        if cert.cert_number:
            parts.append(cert.cert_number.strip())
        else:
            parts.append('证书')
    
    # 连接各部分，移除非法字符
    filename = '_'.join(parts)
    # 移除文件名中的非法字符
    filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '（', '）', '(', ')'))
    filename = filename.replace(' ', '_')
    
    return f'{filename}.pdf'
