from flask import render_template, request, jsonify, redirect, url_for
import os
from werkzeug.utils import secure_filename
from app.models import db, Activity, Certificate
from app.auth import admin_login_required
from app.services.image_service import ImageService
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
    area = request.args.get('area', '')
    name = request.args.get('name', '')
    phone = request.args.get('phone', '')
    id_number = request.args.get('id_number', '')
    project = request.args.get('project', '')
    param_group = request.args.get('param_group', '')
    
    # 获取分页参数
    page = request.args.get('page', 1, type=int)
    per_page_param = request.args.get('per_page', '50')
    
    # 处理per_page参数，支持"all"值
    if per_page_param == 'all':
        per_page = 50000  # 设置为大数值表示显示全部
    else:
        try:
            per_page = int(per_page_param)
        except (ValueError, TypeError):
            per_page = 50  # 默认值
    
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
    if area:
        query = query.filter(Certificate.area.like(f'%{area}%'))
    if name:
        query = query.filter(Certificate.name.like(f'%{name}%'))
    if phone:
        query = query.filter(Certificate.phone.like(f'%{phone}%'))
    if id_number:
        query = query.filter(Certificate.id_number.like(f'%{id_number}%'))
    if project:
        query = query.filter(Certificate.project.like(f'%{project}%'))
    if param_group:
        query = query.filter(Certificate.param_group.like(f'%{param_group}%'))

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
            
        if cert.image_path_backup and os.path.exists(cert.image_path_backup):
            files_to_delete.append(cert.image_path_backup)
        
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
        
        # 更新证书信息 - 支持所有字段
        cert.cert_number = data.get('cert_number', cert.cert_number)
        cert.unit_name = data.get('unit_name', cert.unit_name)
        cert.area = data.get('area', cert.area)
        cert.name = data.get('name', cert.name)
        cert.id_type = data.get('id_type', cert.id_type)
        cert.id_number = data.get('id_number', cert.id_number)
        cert.gender = data.get('gender', cert.gender)
        
        # 处理年龄字段，确保空值转换为None
        age_value = data.get('age', cert.age)
        if age_value == '' or age_value is None:
            cert.age = None
        else:
            try:
                cert.age = int(age_value) if age_value else None
            except (ValueError, TypeError):
                cert.age = None
        
        # 处理出生日期
        birth_date = data.get('birth_date')
        if birth_date:
            from datetime import datetime
            try:
                cert.birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
            except ValueError:
                cert.birth_date = None
        else:
            cert.birth_date = None
            
        cert.phone = data.get('phone', cert.phone)
        cert.identity = data.get('identity', cert.identity)
        cert.grade_major = data.get('grade_major', cert.grade_major)
        cert.project = data.get('project', cert.project)
        cert.param_group = data.get('param_group', cert.param_group)
        # 注意：image_path 通常不在编辑表单中修改，因为涉及文件操作
        
        # 如果证书已生成，删除旧的证书文件
        if cert.certificate_file and os.path.exists(cert.certificate_file):
            os.remove(cert.certificate_file)
            cert.certificate_file = None
        
        db.session.commit()
        return jsonify({'message': '证书更新成功'})
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
        
        # 处理出生日期
        birth_date = data.get('birth_date')
        birth_date_obj = None
        if birth_date:
            from datetime import datetime
            try:
                birth_date_obj = datetime.strptime(birth_date, '%Y-%m-%d').date()
            except ValueError:
                birth_date_obj = None
        
        # 处理年龄字段
        age_value = data.get('age')
        if age_value == '' or age_value is None:
            age_value = None
        else:
            try:
                age_value = int(age_value) if age_value else None
            except (ValueError, TypeError):
                age_value = None
        
        # 创建新证书 - 支持所有字段
        certificate = Certificate(
            activity_id=activity_id,
            cert_number=data.get('cert_number'),
            unit_name=data.get('unit_name'),
            area=data.get('area'),
            name=data.get('name'),
            id_type=data.get('id_type'),
            id_number=data.get('id_number'),
            gender=data.get('gender'),
            age=age_value,
            birth_date=birth_date_obj,
            phone=data.get('phone'),
            identity=data.get('identity'),
            grade_major=data.get('grade_major'),
            project=data.get('project'),
            param_group=data.get('param_group')
            # image_path 在添加时通常为空，需要单独上传图片
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

@admin_bp.route('/certificate/<int:cert_id>', methods=['GET'])
@admin_login_required
def admin_get_certificate(cert_id):
    """获取单个证书信息"""
    try:
        cert = Certificate.query.get_or_404(cert_id)
        
        # 将证书对象转换为字典
        cert_data = {
            'id': cert.id,
            'cert_number': cert.cert_number,
            'unit_name': cert.unit_name,
            'area': cert.area,
            'name': cert.name,
            'id_type': cert.id_type,
            'id_number': cert.id_number,
            'gender': cert.gender,
            'age': cert.age,
            'birth_date': cert.birth_date.strftime('%Y-%m-%d') if cert.birth_date else '',
            'phone': cert.phone,
            'identity': cert.identity,
            'grade_major': cert.grade_major,
            'project': cert.project,
            'param_group': cert.param_group,
            'image_path': cert.image_path,
            'image_path_backup': cert.image_path_backup,
            'certificate_file': cert.certificate_file,
            'activity_id': cert.activity_id
        }
        
        return jsonify(cert_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@admin_bp.route('/certificate/<int:cert_id>/image', methods=['POST'])
@admin_login_required
def admin_upload_certificate_image(cert_id):
    """上传参与者照片"""
    try:
        cert = Certificate.query.get_or_404(cert_id)
        
        if 'image' not in request.files:
            return jsonify({'error': '未选择图片文件'}), 400
            
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': '未选择图片文件'}), 400
            
        # 检查文件类型
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
        if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({'error': '不支持的图片格式，请上传 PNG、JPG、JPEG、GIF 或 BMP 格式的图片'}), 400
        
        # 获取图片类型（主图片或备用图片）
        image_type = request.form.get('image_type', 'main')
        
        # 初始化图片服务
        image_service = ImageService(app)
        
        # 生成安全的文件名
        original_filename = secure_filename(file.filename)
        suffix = '_backup' if image_type == 'backup' else ''
        name_prefix = f"cert_{cert_id}_{cert.name}{suffix}"
        
        # 保存并处理图片
        result = image_service.save_uploaded_image(file, name_prefix)
        
        if result is None:
            return jsonify({'error': '图片保存失败'}), 500
        
        # 根据图片类型更新对应的字段
        if image_type == 'backup':
            # 删除旧的备用图片
            if cert.image_path_backup and os.path.exists(cert.image_path_backup):
                try:
                    os.remove(cert.image_path_backup)
                except OSError:
                    pass
            # 更新备用图片路径
            cert.image_path_backup = result['relative_path']
            image_url = f"/participant_backup_image/{cert_id}"
            message = '备用图片上传成功'
        else:
            # 删除旧的主图片
            if cert.image_path and os.path.exists(cert.image_path):
                try:
                    os.remove(cert.image_path)
                except OSError:
                    pass
            # 更新主图片路径
            cert.image_path = result['relative_path']
            image_url = f"/participant_image/{cert_id}"
            message = '主图片上传成功'
        
        # 如果证书已生成，删除旧的证书文件（需要重新生成）
        if cert.certificate_file and os.path.exists(cert.certificate_file):
            os.remove(cert.certificate_file)
            cert.certificate_file = None
        
        db.session.commit()
        
        return jsonify({
            'message': message,
            'image_path': result['relative_path'],
            'image_url': image_url,
            'image_type': image_type
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'图片上传失败：{str(e)}'}), 500

@admin_bp.route('/certificate/<int:cert_id>/image', methods=['DELETE'])
@admin_login_required  
def admin_delete_certificate_image(cert_id):
    """删除参与者照片"""
    try:
        cert = Certificate.query.get_or_404(cert_id)
        
        if not cert.image_path:
            return jsonify({'error': '该证书没有图片'}), 404
            
        # 删除图片文件
        if os.path.exists(cert.image_path):
            os.remove(cert.image_path)
            
        # 清空数据库中的图片路径
        cert.image_path = None
        
        # 如果证书已生成，删除旧的证书文件（需要重新生成）
        if cert.certificate_file and os.path.exists(cert.certificate_file):
            os.remove(cert.certificate_file)
            cert.certificate_file = None
            
        db.session.commit()
        
        return jsonify({'message': '图片删除成功'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'图片删除失败：{str(e)}'}), 500 